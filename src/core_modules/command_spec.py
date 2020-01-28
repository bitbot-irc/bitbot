from src import EventManager, ModuleManager, utils

# describing command arg specifications, to centralise parsing and validating.
#
# format: <!|?><name>
#   ! = required
#   ? = optional
#
# if "name" contains "~", it will be marked as an "important" spec
# this means that, e.g. "!r~channel" will be:
#   - marked as important
#   - name split to everything after ~
#   - the name, and it's value, will be offered to other preprocessors.
#
# this means, in practice, that "!r~channel" is a:
#   - "revelant" channel (current if in channel, explicit arg otherwise)
#   - will be used to check if a user has permissions
#
# spec types:
#   - "time" - +1w2d3h4m5s format time
#   - "rchannel" - relevant channel. current channel if we're in channel,
#     otherwise an explicit channel name argument
#   - "channel" - an argument of a channel name
#   - "cuser" - a nickname but only if they are in the current channel
#   - "ruser" - revlevant user. either current user if no arguments, otherwise
#     take nickname for user from given args
#   - "user" - an argument of a user's nickname
#   - "ouser" - an argument of a potentially offline user's nickname
#   - "word" - one word from arguments
#   - "string" - collect all remaining args in to a string

class Module(ModuleManager.BaseModule):
    def _spec_value(self, server, channel, user, argument_types, args):
        options = []
        first_error = None
        for argument_type in argument_types:
            value = None
            n = 0
            error = None

            simple_value, simple_count = argument_type.simple(args)
            if not simple_count == -1:
                value = simple_value
                n = simple_count
                error = argument_type.error()
            elif argument_type.type == "rchannel":
                if channel:
                    value = channel
                elif args:
                    n = 1
                    if args[0] in server.channels:
                        value = server.channels.get(args[0])
                    error = "No such channel"
                else:
                    error = "No channel provided"
            elif argument_type.type == "channel" and args:
                if args[0] in server.channels:
                    value = server.channels.get(args[0])
                n = 1
                error = "No such channel"
            elif argument_type.type == "cuser" and args:
                tuser = server.get_user(args[0], create=False)
                if tuser and channel.has_user(tuser):
                    value = tuser
                n = 1
                error = "That user is not in this channel"
            elif argument_type.type == "ruser":
                if args:
                    value = server.get_user(args[0], create=False)
                    n = 1
                else:
                    value = user
                error = "No such user"
            elif argument_type.type == "user":
                if args:
                    value = server.get_user(args[0], create=False)
                    n = 1
                    error = "No such user"
                else:
                    error = "No user provided"
            elif argument_type.type == "ouser":
                if args:
                    if server.has_user_id(args[0]):
                        value = server.get_user(args[0], create=True)
                    error = "Unknown nickname"
                n = 1
            elif argument_type.type == "nuser":
                if args:
                    value = server.get_user(args[0], create=True)
                n = 1
            elif argument_type.type == "channelonly":
                value = not channel == None
                n = 0
                error = "Command not valid in private message"
            elif argument_type.type == "privateonly":
                value = channel == None
                n = 0
                error = "Command not valid in private message"

            options.append([argument_type, value, n, error])
        return options

    def _argument_types(self, options, args):
        current_error = None
        for argument_type, value, n, error in options:
            if not value == None:
                return [argument_type, n, value]
            elif error:
                current_error = error
            elif n > len(args):
                current_error = "Not enough arguments"
        return [None, -1, current_error or "Invalid arguments"]

    @utils.hook("preprocess.command")
    @utils.kwarg("priority", EventManager.PRIORITY_HIGH)
    def preprocess(self, event):
        specs = event["hook"].get_kwargs("spec")
        if specs:
            server = event["server"]
            channel = event["target"] if event["is_channel"] else None
            user = event["user"]

            overall_error = None
            best_count = 0
            for spec_arguments in specs:
                out = {}
                args = event["args_split"].copy()
                kwargs = {"channel": channel}
                failed = False

                current_error = None
                count = 0
                for i, spec_argument in enumerate(spec_arguments):
                    argument_type_multi = len(set(
                        t.type for t in spec_argument.types)) > 1
                    options = self._spec_value(server, kwargs["channel"], user,
                        spec_argument.types, args)

                    argument_type, n, value = self._argument_types(options, args)
                    if n > -1:
                        args = args[n:]

                        if argument_type.exported:
                            kwargs[argument_type.exported] = value

                        if argument_type_multi:
                            value = [argument_type.type, value]

                    elif not spec_argument.optional:
                        failed = True
                        current_error = value
                        break
                    else:
                        value = None

                    if not argument_type == None and spec_argument.consume:
                        out[i] = value
                        argument_type_name = argument_type.name()
                        if argument_type_name:
                            out[argument_type_name] = value

                if not failed:
                    kwargs["spec"] = out
                    event["kwargs"].update(kwargs)
                    return
                else:
                    if count >= best_count:
                        overall_error = current_error

            return utils.consts.PERMISSION_HARD_FAIL, overall_error
