import re
from src import EventManager, ModuleManager, Utils

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
            self.target.send_message(text, prefix=Utils.FONT_RESET + "[%s] " %
                                                         self.prefix())
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

@Utils.export("channelset", {"setting": "command-prefix",
    "help": "Set the command prefix used in this channel"})
@Utils.export("serverset", {"setting": "command-prefix",
    "help": "Set the command prefix used on this server"})
@Utils.export("serverset", {"setting": "identity-mechanism",
    "help": "Set the identity mechanism for this server"})
class Module(ModuleManager.BaseModule):
    @Utils.hook("new.user|channel")
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

            module_name = ""
            if hasattr(hook.function, "__self__"):
                module_name = hook.function.__self__._name
            stdout, stderr = StdOut(module_name, target), StdErr(module_name,
                target)

            returns = self.events.on("preprocess.command"
                ).call(hook=hook, user=event["user"], server=event["server"],
                target=target, is_channel=is_channel, tags=event["tags"])
            for returned in returns:
                if returned:
                    stderr.write(returned).send()
                    target.buffer.skip_next()
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
                    target=target, args=args,
                    args_split=args_split, stdout=stdout, stderr=stderr,
                    command=command.lower(), is_channel=is_channel,
                    tags=event["tags"])
                if not hook.kwargs.get("skip_out", False):
                    stdout.send()
                    stderr.send()
                    target.last_stdout = stdout
                    target.last_stderr = stderr
            target.buffer.skip_next()
        event.eat()

    @Utils.hook("received.message.channel", priority=EventManager.PRIORITY_LOW)
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

    @Utils.hook("received.message.private", priority=EventManager.PRIORITY_LOW)
    def private_message(self, event):
        if event["message_split"]:
            command = event["message_split"][0].lower()
            self.message(event, command)

    def _get_help(self, hook):
        return hook.get_kwarg("help", None) or hook.docstring.description
    def _get_usage(self, hook):
        return hook.get_kwarg("usage", None)

    @Utils.hook("received.command.help")
    def help(self, event):
        """
        :help: Show help for a given command
        :usage: [command]
        """
        if event["args"]:
            command = event["args_split"][0].lower()
            if command in self.events.on("received").on(
                    "command").get_children():
                hooks = self.events.on("received.command").on(command).get_hooks()
                help = self._get_help(hooks[0])

                if help:
                    event["stdout"].write("%s: %s" % (command, help))
                else:
                    event["stderr"].write("No help available for %s" % command)
            else:
                event["stderr"].write("Unknown command '%s'" % command)
        else:
            help_available = []
            for child in self.events.on("received.command").get_children():
                hooks = self.events.on("received.command").on(child).get_hooks()

                if hooks and self._get_help(hooks[0]):
                    help_available.append(child)
            help_available = sorted(help_available)
            event["stdout"].write("Commands: %s" % ", ".join(help_available))

    @Utils.hook("received.command.usage", min_args=1)
    def usage(self, event):
        """
        :help: Show the usage for a given command
        :usage: <command>
        """
        command_prefix = ""
        if event["is_channel"]:
            command_prefix = event["target"].get_setting("command-prefix",
                event["server"].get_setting("command-prefix", "!"))

        command = event["args_split"][0].lower()
        if command in self.events.on("received").on(
                "command").get_children():
            hooks = self.events.on("received.command").on(command).get_hooks()
            usage = self._get_usage(hooks[0])

            if usage:
                event["stdout"].write("Usage: %s%s %s" % (command_prefix,
                    command, usage))
            else:
                event["stderr"].write("No usage help available for %s" % command)
        else:
            event["stderr"].write("Unknown command '%s'" % command)

    @Utils.hook("received.command.more", skip_out=True)
    def more(self, event):
        """
        :help: Show more output from the last command
        """
        if event["target"].last_stdout and event["target"].last_stdout.has_text():
            event["target"].last_stdout.send()

    @Utils.hook("received.command.ignore", min_args=1)
    def ignore(self, event):
        """
        :help: Ignore commands from a given user
        :usage: <nickname>
        :permission: ignore
        """
        user = event["server"].get_user(event["args_split"][0])
        if user.get_setting("ignore", False):
            event["stderr"].write("I'm already ignoring '%s'" %
                user.nickname)
        else:
            user.set_setting("ignore", True)
            event["stdout"].write("Now ignoring '%s'" % user.nickname)

    @Utils.hook("received.command.unignore", min_args=1)
    def unignore(self, event):
        """
        :help: Unignore commands from a given user
        :usage: <nickname>
        :permission: unignore
        """
        user = event["server"].get_user(event["args_split"][0])
        if not user.get_setting("ignore", False):
            event["stderr"].write("I'm not ignoring '%s'" % user.nickname)
        else:
            user.set_setting("ignore", False)
            event["stdout"].write("Removed ignore for '%s'" % user.nickname)

    @Utils.hook("send.stdout")
    def send_stdout(self, event):
        stdout = StdOut(event["module_name"], event["target"])
        stdout.write(event["message"]).send()
        if stdout.has_text():
            event["target"].last_stdout = stdout
    @Utils.hook("send.stderr")
    def send_stderr(self, event):
        stderr = StdErr(event["module_name"], event["target"])
        stderr.write(event["message"]).send()
        if stderr.has_text():
            event["target"].last_stderr = stderr
