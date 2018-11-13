import re
from src import EventManager, ModuleManager, utils

STR_MORE = "%s (more...)" % utils.consts.RESET
STR_CONTINUED = "(...continued) "

COMMAND_METHOD = "command-method"
COMMAND_METHODS = ["PRIVMSG", "NOTICE"]

OUT_CUTOFF = 400

REGEX_CUTOFF = re.compile("^.{1,%d}(?:\s|$)" % OUT_CUTOFF)

class Out(object):
    def __init__(self, server, module_name, target, msgid):
        self.server = server
        self.module_name = module_name
        self._hide_prefix = False
        self.target = target
        self._text = ""
        self.written = False
        self._msgid = msgid

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

            tags = {}
            if self._msgid:
                tags["+draft/reply"] = self._msgid

            prefix = ""
            if not self._hide_prefix:
                prefix = utils.consts.RESET + "[%s] " % self.prefix()

            method = self._get_method()
            if method == "PRIVMSG":
                self.target.send_message(text, prefix=prefix, tags=tags)
            elif method == "NOTICE":
                self.target.send_notice(text, prefix=prefix, tags=tags)

    def _get_method(self):
        return self.target.get_setting(COMMAND_METHOD,
            self.server.get_setting(COMMAND_METHOD, "PRIVMSG")).upper()

    def set_prefix(self, prefix):
        self.module_name = prefix
    def hide_prefix(self):
        self._hide_prefix = True

    def has_text(self):
        return bool(self._text)


class StdOut(Out):
    def prefix(self):
        return utils.irc.color(utils.irc.bold(self.module_name),
            utils.consts.GREEN)
class StdErr(Out):
    def prefix(self):
        return utils.irc.color(utils.irc.bold("!"+self.module_name),
            utils.consts.RED)

def _command_method_validate(s):
    if s.upper() in COMMAND_METHODS:
        return s.upper()

@utils.export("channelset", {"setting": "command-prefix",
    "help": "Set the command prefix used in this channel"})
@utils.export("serverset", {"setting": "command-prefix",
    "help": "Set the command prefix used on this server"})
@utils.export("serverset", {"setting": "command-method",
    "help": "Set the method used to respond to commands",
    "validate": _command_method_validate})
@utils.export("channelset", {"setting": "command-method",
    "help": "Set the method used to respond to commands",
    "validate": _command_method_validate})
@utils.export("channelset", {"setting": "hide-prefix",
    "help": "Disable/enable hiding prefix in command reponses",
    "validate": utils.bool_or_none})
@utils.export("channelset", {"setting": "commands",
    "help": "Disable/enable responding to commands in-channel",
    "validate": utils.bool_or_none})
@utils.export("channelset", {"setting": "prefixed-commands",
    "help": "Disable/enable responding to prefixed commands in-channel",
    "validate": utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    @utils.hook("new.user|channel")
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
            alias_of = self._get_alias_of(hook)
            if alias_of:
                if self.has_command(alias_of):
                    hook = self.get_hook(alias_of)
                else:
                    raise ValueError("'%s' is an alias of unknown command '%s'"
                        % (command.lower(), alias_of.lower()))
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

            module_name = self._get_prefix(hook) or ""
            if not module_name and hasattr(hook.function, "__self__"):
                module_name = hook.function.__self__._name

            msgid = event["tags"].get("draft/msgid", None)
            stdout = StdOut(event["server"], module_name, target, msgid)
            stderr = StdErr(event["server"], module_name, target, msgid)

            returns = self.events.on("preprocess.command").call_unsafe(
                hook=hook, user=event["user"], server=event["server"],
                target=target, is_channel=is_channel, tags=event["tags"])
            for returned in returns:
                if returned == False:
                    # denotes a "silent failure"
                    target.buffer.skip_next()
                    return
                if returned:
                    # error message
                    stderr.write(returned).send()
                    target.buffer.skip_next()
                    return

            args_split = event["message_split"][args_index:]
            if hook.kwargs.get("remove_empty", True):
                args_split = list(filter(None, args_split))

            min_args = hook.kwargs.get("min_args")
            if min_args and len(args_split) < min_args:
                usage = self._get_usage(hook, command)
                if usage:
                    stderr.write("Not enough arguments, usage: %s" %
                        usage).send()
                else:
                    stderr.write("Not enough arguments (minimum: %d)" %
                        min_args).send()
            else:
                args = " ".join(args_split)
                server = event["server"]
                user = event["user"]
                try:
                    self.events.on("received.command").on(command
                        ).call_unsafe_limited(1, user=user, server=server,
                        target=target, args=args, tags=event["tags"],
                        args_split=args_split, stdout=stdout, stderr=stderr,
                        command=command.lower(), is_channel=is_channel)
                except utils.EventError as e:
                    stderr.write(str(e))

                if not hook.kwargs.get("skip_out", False):
                    stdout.send()
                    stderr.send()
                    target.last_stdout = stdout
                    target.last_stderr = stderr
            target.buffer.skip_next()
        event.eat()

    @utils.hook("received.message.channel", priority=EventManager.PRIORITY_LOW)
    def channel_message(self, event):
        commands_enabled = event["channel"].get_setting("commands", True)
        if not commands_enabled:
            return
        prefixed_commands = event["channel"].get_setting("prefixed-commands", True)

        command_prefix = event["channel"].get_setting("command-prefix",
            event["server"].get_setting("command-prefix", "!"))
        if event["message_split"][0].startswith(command_prefix):
            if not prefixed_commands:
                return
            command = event["message_split"][0].replace(
                command_prefix, "", 1).lower()
            self.message(event, command)
        elif len(event["message_split"]) > 1 and self.is_highlight(
                event["server"], event["message_split"][0]):
            command = event["message_split"][1].lower()
            self.message(event, command, 2)

    @utils.hook("received.message.private", priority=EventManager.PRIORITY_LOW)
    def private_message(self, event):
        if event["message_split"]:
            command = event["message_split"][0].lower()
            self.message(event, command)

    def _get_help(self, hook):
        return hook.get_kwarg("help", None) or hook.docstring.description
    def _get_usage(self, hook, command):
        usage = hook.get_kwarg("usage", None)
        if not usage:
            usages = hook.docstring.var_items.get("usage", None)
            if usages:
                return " | ".join(
                    "%s %s" % (command, usage) for usage in usages)
        return usage

    def _get_prefix(self, hook):
        return hook.get_kwarg("prefix", None)
    def _get_alias_of(self, hook):
        return hook.get_kwarg("alias_of", None)

    @utils.hook("received.command.help")
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

                if hooks and self._get_help(hooks[0]
                        ) and not self._get_alias_of(hooks[0]):
                    help_available.append(child)

            help_available = sorted(help_available)
            event["stdout"].write("Commands: %s" % ", ".join(help_available))

    @utils.hook("received.command.usage", min_args=1)
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
            command_str = "%s%s" % (command_prefix, command)
            hooks = self.events.on("received.command").on(command).get_hooks()
            usage = self._get_usage(hooks[0], command_str)

            if usage:
                event["stdout"].write("Usage: %s" % usage)
            else:
                event["stderr"].write("No usage help available for %s" % command)
        else:
            event["stderr"].write("Unknown command '%s'" % command)

    @utils.hook("received.command.more", skip_out=True)
    def more(self, event):
        """
        :help: Show more output from the last command
        """
        if event["target"].last_stdout and event["target"].last_stdout.has_text():
            event["target"].last_stdout.send()

    @utils.hook("received.command.ignore", min_args=1)
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

    @utils.hook("received.command.unignore", min_args=1)
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

    @utils.hook("send.stdout")
    def send_stdout(self, event):
        stdout = StdOut(event["server"], event["module_name"],
            event["target"], event.get("msgid", None))

        if event.get("hide_prefix", False):
            stdout.hide_prefix()

        stdout.write(event["message"]).send()
        if stdout.has_text():
            event["target"].last_stdout = stdout
    @utils.hook("send.stderr")
    def send_stderr(self, event):
        stderr = StdErr(event["server"], event["module_name"],
            event["target"], event.get("msgid", None))

        if event.get("hide_prefix", False):
            stderr.hide_prefix()

        stderr.write(event["message"]).send()
        if stderr.has_text():
            event["target"].last_stderr = stderr
