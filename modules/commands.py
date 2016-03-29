
STR_MORE = " (more...)"
STR_CONTINUED = "(...continued) "

OUT_CUTOFF = 400

class ChannelOut(object):
    def __init__(self, module_name, channel):
        self.module_name = module_name
        self.channel = channel
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
            self.channel.send_message(text)
    def set_prefix(self, prefix):
        self.module_name = prefix
    def has_text(self):
        return bool(self._text)

class ChannelStdOut(ChannelOut):
    def prefix(self):
        return self.module_name
class ChannelStdErr(ChannelOut):
    def prefix(self):
        return "!%s" % self.module_name

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("message").on("channel").hook(
            self.channel_message)
        bot.events.on("received").on("message").on("private").hook(
            self.private_message)
        bot.events.on("received").on("command").on("help").hook(self.help)
        bot.events.on("new").on("user", "channel").hook(self.new)
        bot.events.on("received").on("command").on("more").hook(self.more)
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

    def channel_message(self, event):
        command_prefix = event["channel"].get_setting("command_prefix",
            event["server"].get_setting("command_prefix", "!"))
        if event["message_split"][0].startswith(command_prefix):
            command = event["message_split"][0].replace(
                command_prefix, "", 1).lower()
            if self.has_command(command):
                hook = self.get_hook(command)
                module_name = hook.function.__self__._name
                stdout = ChannelStdOut(module_name, event["channel"])
                stderr = ChannelStdErr(module_name, event["channel"])
                returns = self.bot.events.on("preprocess").on("command"
                    ).call(hook=hook, user=event["user"], server=event[
                    "server"])
                for returned in returns:
                    if returned:
                        event["stderr"].write(returned).send()
                        return
                min_args = hook.kwargs.get("min_args")
                # get rid of all the empty strings
                args_split = list(filter(None, event["message_split"][1:]))
                if min_args and len(args_split) < min_args:
                    ChannelStdErr("Error", event["channel"]
                        ).write("Not enough arguments ("
                        "minimum: %d)" % min_args).send()
                else:
                    args = " ".join(args_split)
                    self.bot.events.on("received").on("command").on(
                        command).call(1, user=event["user"],
                        channel=event["channel"], args=args,
                        args_split=args_split, server=event["server"
                        ], stdout=stdout, stderr=stderr, command=command,
                        log=event["channel"].log, target=event["channel"])
                    stdout.send()
                    stderr.send()
                    if stdout.has_text():
                        event["channel"].last_stdout = stdout
                    if stderr.has_text():
                        event["channel"].last_stderr = stderr
                event["channel"].log.skip_next()
    def private_message(self, event):
        pass

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
        if event["target"].last_stdout:
            event["target"].last_stdout.send()

    def send_stdout(self, event):
        if event["target"].name[0] in event["server"].channel_types:
            stdout = ChannelStdOut(event["module_name"], event["target"])
        stdout.write(event["message"]).send()
        if stdout.has_text():
            event["target"].last_stdout = stdout
    def send_stderr(self, event):
        if event["target"].name[0] in event["server"].channel_types:
            stderr = ChannelStdErr(event["module_name"], event["target"])
        stderr.write(event["message"]).send()
        if stderr.has_text():
            event["target"].last_stderr = stderr

