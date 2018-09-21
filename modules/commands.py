import re
import EventManager, Utils

STR_MORE = "%s (more...)" % Utils.FONT_RESET
STR_CONTINUED = "(...continued) "

OUT_CUTOFF = 400

REGEX_CUTOFF = re.compile("^.{1,%d}(?:\s|$)" % OUT_CUTOFF)

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
            text = self._text
            text_encoded = text.encode("utf8")
            if len(text_encoded) > OUT_CUTOFF:
                text = "%s%s" % (text_encoded[:OUT_CUTOFF].decode("utf8"
                    ).rstrip(), STR_MORE)
                self._text = "%s%s" % (STR_CONTINUED, text_encoded[OUT_CUTOFF:
                    ].decode("utf8").lstrip())
            else:
                self._text = ""
            self.target.send_message(text, prefix="[%s] " % self.prefix())
    def set_prefix(self, prefix):
        self.module_name = prefix
    def has_text(self):
        return bool(self._text)

class StdOut(Out):
    def prefix(self):
        return Utils.color(Utils.bold(self.module_name), Utils.COLOR_GREEN)
class StdErr(Out):
    def prefix(self):
        return Utils.color(Utils.bold(self.module_name), Utils.COLOR_RED)

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        self.events = events
        events.on("received.message.channel").hook(self.channel_message,
            priority=EventManager.PRIORITY_LOW)
        events.on("received.message.private").hook(self.private_message,
            priority=EventManager.PRIORITY_LOW)

        events.on("received.command.help").hook(self.help,
            help="Show help for commands", usage="<command>")
        events.on("received.command.usage").hook(self.usage, min_args=1,
            help="Show usage help for commands", usage="<command>")
        events.on("received.command.more").hook(self.more, skip_out=True,
            help="Get more output from the last command")
        events.on("received.command.ignore").hook(self.ignore, min_args=1,
            help="Ignore commands from a given user", usage="<nickname>",
            permission="ignore")
        events.on("received.command.unignore").hook(self.unignore, min_args=1,
            help="Unignore commands from a given user", usage="<nickname>",
            permission="unignore")

        events.on("new").on("user", "channel").hook(self.new)
        events.on("send.stdout").hook(self.send_stdout)
        events.on("send.stderr").hook(self.send_stderr)

        exports.add("channelset", {"setting": "command-prefix",
            "help": "Set the command prefix used in this channel"})
        exports.add("serverset", {"setting": "command-prefix",
            "help": "Set the command prefix used on this server"})
        exports.add("serverset", {"setting": "identity-mechanism",
            "help": "Set the identity mechanism for this server"})

    def new(self, event):
        if "user" in event:
            target = event["user"]
        else:
            target = event["channel"]
        target.last_stdout = None
        target.last_stderr = None

    def has_command(self, command):
        return command.lower() in self.events.on("received").on(
            "command").get_children()
    def get_hook(self, command):
        return self.events.on("received.command").on(command
            ).get_hooks()[0]

    def is_highlight(self, server, s):
        if s and s[-1] in [":", ","]:
            s = s[:-1]
        return server.is_own_nickname(s)

    def message(self, event, command, args_index=1):
        if self.has_command(command):
            ignore = event["user"].get_setting("ignore", False)
            if ignore:
                return

            hook = self.get_hook(command)
            is_channel = False

            if "channel" in event:
                target = event["channel"]
                is_channel = True
            else:
                target = event["user"]
            if not is_channel and hook.kwargs.get("channel_only"):
                return
            if is_channel and hook.kwargs.get("private_only"):
                return

            buffer = target.buffer

            module_name = hook.function.__self__._name
            stdout, stderr = StdOut(module_name, target), StdErr(module_name,
                target)

            returns = self.events.on("preprocess.command"
                ).call(hook=hook, user=event["user"], server=event["server"],
                target=target, is_channel=is_channel, tags=event["tags"])
            for returned in returns:
                if returned:
                    stderr.write(returned).send()
                    buffer.skip_next()
                    return
            args_split = event["message_split"][args_index:]
            min_args = hook.kwargs.get("min_args")
            if min_args and len(args_split) < min_args:
                if "usage" in hook.kwargs:
                    stderr.write("Not enough arguments, usage: %s %s" % (
                        command, hook.kwargs["usage"])).send()
                else:
                    stderr.write("Not enough arguments (minimum: %d)" % min_args
                       ).send()
            else:
                args = " ".join(args_split)
                server = event["server"]
                user = event["user"]
                self.events.on("received.command").on(command
                    ).call_limited(1, user=user, server=server,
                    target=target, buffer=buffer, args=args,
                    args_split=args_split, stdout=stdout, stderr=stderr,
                    command=command.lower(), is_channel=is_channel,
                    tags=event["tags"])
                if not hook.kwargs.get("skip_out", False):
                    stdout.send()
                    stderr.send()
                    target.last_stdout = stdout
                    target.last_stderr = stderr
            buffer.skip_next()
        event.eat()

    def channel_message(self, event):
        command_prefix = event["channel"].get_setting("command-prefix",
            event["server"].get_setting("command-prefix", "!"))
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
            if command in self.events.on("received").on(
                    "command").get_children():
                hooks = self.events.on("received.command").on(command).get_hooks()
                if hooks and "help" in hooks[0].kwargs:
                    event["stdout"].write("%s: %s" % (command, hooks[0].kwargs["help"]))
                else:
                    event["stderr"].write("No help available for %s" % command)
            else:
                event["stderr"].write("Unknown command '%s'" % command)
        else:
            help_available = []
            for child in self.events.on("received.command").get_children():
                hooks = self.events.on("received.command").on(child).get_hooks()
                if hooks and "help" in hooks[0].kwargs:
                    help_available.append(child)
            help_available = sorted(help_available)
            event["stdout"].write("Commands: %s" % ", ".join(help_available))

    def usage(self, event):
        command_prefix = ""
        if event["is_channel"]:
            command_prefix = event["target"].get_setting("command-prefix",
                event["server"].get_setting("command-prefix", "!"))

        command = event["args_split"][0].lower()
        if command in self.events.on("received").on(
                "command").get_children():
            hooks = self.events.on("received.command").on(command).get_hooks()
            if hooks and "usage" in hooks[0].kwargs:
                event["stdout"].write("Usage: %s%s %s" % (command_prefix,
                    command, hooks[0].kwargs["usage"]))
            else:
                event["stderr"].write("No usage help available for %s" % command)
        else:
            event["stderr"].write("Unknown command '%s'" % command)

    def more(self, event):
        if event["target"].last_stdout and event["target"].last_stdout.has_text():
            event["target"].last_stdout.send()

    def ignore(self, event):
        user = event["server"].get_user(event["args_split"][0])
        if user.get_setting("ignore", False):
            event["stderr"].write("I'm already ignoring '%s'" %
                user.nickname)
        else:
            user.set_setting("ignore", True)
            event["stdout"].write("Now ignoring '%s'" % user.nickname)

    def unignore(self, event):
        user = event["server"].get_user(event["args_split"][0])
        if not user.get_setting("ignore", False):
            event["stderr"].write("I'm not ignoring '%s'" % user.nickname)
        else:
            user.set_setting("ignore", False)
            event["stdout"].write("Removed ignore for '%s'" % user.nickname)

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
