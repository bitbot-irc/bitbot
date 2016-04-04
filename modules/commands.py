import Utils

STR_MORE = " (more...)"
STR_CONTINUED = "(...continued) "

OUT_CUTOFF = 400

class Out(object):
    def __init__(self, module_name, target):
        self.module_name = module_name
        self.target = target
        self._text = ""
        self.written = False
    def write(self, text):
        self._text += text
        self.written = True
        return self
    def send(self):
        if self.has_text():
            text = "[%s] %s" % (self.prefix(), self._text)
            text_encoded = text.encode("utf8")
            if len(text_encoded) > OUT_CUTOFF:
                text = "%s%s" % (text_encoded[:OUT_CUTOFF].decode("utf8"
                    ).rstrip(), STR_MORE)
                self._text = "%s%s" % (STR_CONTINUED, text_encoded[OUT_CUTOFF:
                    ].decode("utf8").lstrip())
            self.target.send_message(text)
    def set_prefix(self, prefix):
        self.module_name = prefix
    def has_text(self):
        return bool(self._text)

class StdOut(Out):
    def prefix(self):
        return "%s%s%s" % (Utils.color(Utils.COLOR_GREEN),
            self.module_name, Utils.FONT_RESET)
class StdErr(Out):
    def prefix(self):
        return "%s!%s%s" % (Utils.color(Utils.COLOR_RED),
            self.module_name, Utils.FONT_RESET)

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("message").on("channel").hook(
            self.channel_message)
        bot.events.on("received").on("message").on("private").hook(
            self.private_message)
        bot.events.on("received").on("command").on("help").hook(self.help,
            help="Show help on commands")
        bot.events.on("received").on("command").on("more").hook(self.more,
            help="Get more output from the last command")
        bot.events.on("new").on("user", "channel").hook(self.new)
        bot.events.on("send").on("stdout").hook(self.send_stdout)
        bot.events.on("send").on("stderr").hook(self.send_stderr)

    def new(self, event):
        if "user" in event:
            target = event["user"]
        else:
            target = event["channel"]
        target.last_stdout = None
        target.last_stderr = None

    def has_command(self, command):
        return command.lower() in self.bot.events.on("received").on(
            "command").get_children()
    def get_hook(self, command):
        return self.bot.events.on("received").on("command").on(command
            ).get_hooks()[0]

    def is_highlight(self, server, s):
        return s.lower() == server.nickname_lower or (s.lower().startswith(
            server.nickname_lower) and len(s) == len(server.nickname_lower
            )+1 and s[-1] in [":", ","])

    def message(self, event, command, args_index=1):
        if self.has_command(command):
            hook = self.get_hook(command)
            is_channel = False

            if "channel" in event:
                target = event["channel"]
                is_channel = True
            else:
                target = event["user"]
            if not is_channel and hook.kwargs.get("channel_only"):
                return
            if is_channel and hooks.kwargs.get("private_only"):
                return

            log = target.log

            module_name = hook.function.__self__._name
            stdout, stderr = StdOut(module_name, target), StdErr(module_name,
                target)

            returns = self.bot.events.on("preprocess").on("command"
                ).call(hook=hook, user=event["user"], server=event["server"])
            for returned in returns:
                if returned:
                    stderr.write(returned).send()
                    log.skip_next()
                    return
            args_split = list(filter(None, event["message_split"][args_index:]))
            min_args = hook.kwargs.get("min_args")
            if min_args and len(args_split) < min_args:
                stderr.write("Not enough arguments (minimum: %d)" % min_args
                    ).send()
            else:
                args = " ".join(args_split)
                server = event["server"]
                user = event["user"]
                self.bot.events.on("received").on("command").on(command).call(
                    1, user=user, server=server, target=target, log=log,
                    args=args, args_split=args_split, stdout=stdout, stderr=stderr,
                    command=command.lower())
                stdout.send()
                target.last_stdout = stdout
                stderr.send()
                target.last_stderr = stderr
            log.skip_next()


    def channel_message(self, event):
        command_prefix = event["channel"].get_setting("command_prefix",
            event["server"].get_setting("command_prefix", "!"))
        if event["message_split"][0].startswith(command_prefix):
            command = event["message_split"][0].replace(
                command_prefix, "", 1).lower()
            self.message(event, command)
        elif len(event["message_split"]) > 1 and self.is_highlight(
                event["server"], event["message_split"][0]):
            command = event["message_split"][1].lower()
            self.message(event, command, 2)

    def private_message(self, event):
        if event["message_split"]:
            command = event["message_split"][0].lower()
            self.message(event, command)

    def help(self, event):
        if event["args"]:
            command = event["args_split"][0].lower()
            if command in self.bot.events.on("received").on(
                    "command").get_children():
                hooks = self.bot.events.on("received").on("command").on(command).get_hooks()
                if hooks and "help" in hooks[0].kwargs:
                    event["stdout"].write("%s: %s" % (command, hooks[0].kwargs["help"]))
        else:
            help_available = []
            for child in self.bot.events.on("received").on("command").get_children():
                hooks = self.bot.events.on("received").on("command").on(child).get_hooks()
                if hooks and "help" in hooks[0].kwargs:
                    help_available.append(child)
            help_available = sorted(help_available)
            event["stdout"].write("Commands: %s" % ", ".join(help_available))

    def more(self, event):
        if event["target"].last_stdout and event["target"].last_stdout.has_text():
            event["target"].last_stdout.send()

    def send_stdout(self, event):
        stdout = StdOut(event["module_name"], event["target"])
        stdout.write(event["message"]).send()
        if stdout.has_text():
            event["target"].last_stdout = stdout
    def send_stderr(self, event):
        stderr = StdErr(event["module_name"], event["target"])
        stderr.write(event["message"]).send()
        if stderr.has_text():
            event["target"].last_stderr = stderr

