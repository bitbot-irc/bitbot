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

            if spec_type == "time" and args:
                time, _ = utils.parse.timed_args(args)
                chunk = time
                n = 1
                error = "Invalid timeframe"
            elif spec_type == "rchannel":
                if channel:
                    chunk = channel
                elif args:
                    n = 1
                    if args[0] in server.channels:
                        chunk = server.channels.get(args[0])
                    error = "No such channel"
                else:
                    error = "No channel provided"
            elif spec_type == "channel" and args:
                if args[0] in server.channels:
                    chunk = server.channels.get(args[0])
                n = 1
                error = "No such channel"
            elif spec_type == "cuser" and args:
                tuser = server.get_user(args[0], create=False)
                if tuser and channel.has_user(tuser):
                    chunk = tuser
                n = 1
                error = "That user is not in this channel"
            elif spec_type == "ruser":
                if args:
                    chunk = server.get_user(args[0], create=False)
                    n = 1
                else:
                    chunk = user
                error = "No such user"
            elif spec_type == "user":
                if args:
                    chunk = server.get_user(args[0], create=False)
                    n = 1
                    error = "No such user"
                else:
                    error = "No user provided"
            elif spec_type == "ouser" and args:
                if server.has_user_id(args[0]):
                    chunk = server.get_user(args[0])
                n = 1
                error = "Unknown nickname"
            elif spec_type == "word" and args:
                chunk = args[0]
                n = 1
            elif spec_type == "...":
                chunk = " ".join(args)
                n = len(args)

            options.append([chunk, n, error])
        return options

    @utils.hook("preprocess.command")
    @utils.kwarg("priority", EventManager.PRIORITY_HIGH)
    def preprocess(self, event):
        spec = event["hook"].get_kwarg("spec", None)
        if not spec == None:
            server = event["server"]
            channel = event["target"] if event["is_channel"] else None
            user = event["user"]
            args = event["args_split"].copy()

            out = []
            for word in spec.split():
                optional = word[0] == "?"
                word = word[1:]

                raw_spec_types = word.split("|")
                spec_types = [t.replace("~", "", 1) for t in raw_spec_types]

                options = self._spec_chunk(server, channel, user, spec_types, args)

                found = None
                first_error = None
                for i, (chunk, n, error) in enumerate(options):
                    spec_type = spec_types[i]
                    raw_spec_type = raw_spec_types[i]

                    if error and not first_error:
                        first_error = error

                    if chunk:
                        if "~" in raw_spec_type:
                            event["kwargs"][raw_spec_type.split("~", 1)[1]] = chunk

                        found = True
                        args = args[n:]
                        if len(spec_types) > 1:
                            chunk = [spec_type, chunk]
                        found = chunk
                        break
                out.append(found)

                if not optional and not found:
                    error = first_error or "Invalid arguments"
                    return utils.consts.PERMISSION_HARD_FAIL, error
            event["kwargs"]["spec"] = out
