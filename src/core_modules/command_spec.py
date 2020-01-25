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
#   - "..." - collect all remaining args in to a string

class Module(ModuleManager.BaseModule):
    def _spec_chunk(self, server, channel, user, spec_types, args):
        options = []
        first_error = None
        for spec_type in spec_types:
            chunk = None
            n = 0
            error = None

            if spec_type.name == "time" and args:
                time, _ = utils.parse.timed_args(args)
                chunk = time
                n = 1
                error = "Invalid timeframe"
            elif spec_type.name == "rchannel":
                if channel:
                    chunk = channel
                elif args:
                    n = 1
                    if args[0] in server.channels:
                        chunk = server.channels.get(args[0])
                    error = "No such channel"
                else:
                    error = "No channel provided"
            elif spec_type.name == "channel" and args:
                if args[0] in server.channels:
                    chunk = server.channels.get(args[0])
                n = 1
                error = "No such channel"
            elif spec_type.name == "cuser" and args:
                tuser = server.get_user(args[0], create=False)
                if tuser and channel.has_user(tuser):
                    chunk = tuser
                n = 1
                error = "That user is not in this channel"
            elif spec_type.name == "ruser":
                if args:
                    chunk = server.get_user(args[0], create=False)
                    n = 1
                else:
                    chunk = user
                error = "No such user"
            elif spec_type.name == "user":
                if args:
                    chunk = server.get_user(args[0], create=False)
                    n = 1
                    error = "No such user"
                else:
                    error = "No user provided"
            elif spec_type.name == "ouser" and args:
                if server.has_user_id(args[0]):
                    chunk = server.get_user(args[0])
                n = 1
                error = "Unknown nickname"
            elif spec_type.name == "word":
                if args:
                    chunk = args[0]
                n = 1
            elif spec_type.name == "...":
                if args:
                    chunk = " ".join(args)
                n = max(1, len(args))

            options.append([spec_type, chunk, n, error])
        return options

    @utils.hook("preprocess.command")
    @utils.kwarg("priority", EventManager.PRIORITY_HIGH)
    def preprocess(self, event):
        spec_types = event["hook"].get_kwarg("spec", None)
        if not spec_types == None:
            server = event["server"]
            channel = event["target"] if event["is_channel"] else None
            user = event["user"]
            args = event["args_split"].copy()

            out = []
            kwargs = {"channel": channel}

            for item in spec_types:
                options = self._spec_chunk(server, kwargs["channel"], user,
                    item.types, args)

                found = None
                first_error = None
                for spec_type, chunk, n, error in options:
                    if not chunk == None:
                        if spec_type.exported:
                            kwargs[spec_type.exported] = chunk

                        found = True
                        args = args[n:]
                        if len(item.types) > 1:
                            chunk = [spec_type, chunk]
                        found = chunk
                        break
                    elif not error and n > 0:
                        error = "Not enough arguments"

                    if error and not first_error:
                        first_error = error

                out.append(found)

                if not item.optional and not found:
                    error = first_error or "Invalid arguments"
                    return utils.consts.PERMISSION_HARD_FAIL, error

            kwargs["spec"] = out
            event["kwargs"].update(kwargs)
