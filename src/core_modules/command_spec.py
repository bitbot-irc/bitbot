from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _spec_chunk(self, server, channel, user, types, args):
        options = []
        first_error = None
        for type in types:
            chunk = None
            n = 0
            error = None

            if type == "time" and args:
                time, _ = utils.parse.timed_args(args)
                chunk = time
                n = 1
                error = "Invalid timeframe"
            elif type == "rchannel":
                if channel:
                    chunk = channel
                else:
                    n = 1
                    if args[0] in server.channels:
                        chunk = server.channels.get(args[0])
                error = "No such channel"
            elif type == "channel" and args:
                if args[0] in server.channels:
                    chunk = server.channels.get(args[0])
                n = 1
                error = "No such channel"
            elif type == "cuser" and args:
                tuser = server.get_user(args[0], create=False)
                if tuser and channel.has_user(tuser):
                    chunk = tuser
                n = 1
                error = "That user is not in this channel"
            elif type == "ruser":
                if args:
                    chunk = server.get_user(args[0], create=False)
                    n = 1
                else:
                    chunk = user
                error = "No such user"
            elif type == "user" and args:
                chunk = server.get_user(args[0], create=False)
                n = 1
                error = "No such user"
            elif type == "word" and args:
                chunk = args[0]
                n = 1
            elif type == "...":
                chunk = " ".join(args)
                n = len(args)

            options.append([type, chunk, n, error])
        return options

    @utils.hook("preprocess.command")
    def preprocess(self, event):
        spec = event["hook"].get_kwarg("spec", None)
        if not spec == None:
            server = event["server"]
            channel = event["target"] if event["is_channel"] else None
            user = event["user"]
            args = event["args_split"].copy()

            out = []
            for word in spec.split():
                types = word[1:].split("|")
                optional = word[0] == "?"

                options = self._spec_chunk(server, channel, user, types, args)

                found = None
                first_error = None
                for type, chunk, n, error in options:
                    if error and not first_error:
                        first_error = error

                    if chunk:
                        found = True
                        args = args[n:]
                        if len(types) > 1:
                            chunk = [type, chunk]
                        found = chunk
                        break
                out.append(found)

                if not optional and not found:
                    error = first_error or "Invalid arguments"
                    return utils.consts.PERMISSION_HARD_FAIL, error
            event["kwargs"]["spec"] = out
