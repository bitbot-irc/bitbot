#--depends-on config
#--depends-on permissions

import re, string, typing
from src import EventManager, ModuleManager, utils
from . import outs

COMMAND_METHOD = "command-method"
COMMAND_METHODS = ["PRIVMSG", "NOTICE"]

REGEX_ARG_NUMBER = re.compile(r"\$(\d+)(-?)")

MESSAGE_TAGS_CAP = utils.irc.Capability("message-tags",
    "draft/message-tags-0.2")
MSGID_TAG = utils.irc.MessageTag("msgid", "draft/msgid")

NON_ALPHANUMERIC = [char for char in string.printable if not char.isalnum()]

def _command_method_validate(s):
    if s.upper() in COMMAND_METHODS:
        return s.upper()

@utils.export("channelset", {"setting": "command-prefix",
    "help": "Set the command prefix used in this channel", "example": "!"})
@utils.export("serverset", {"setting": "command-prefix",
    "help": "Set the command prefix used on this server", "example": "!"})
@utils.export("serverset", {"setting": "command-method",
    "help": "Set the method used to respond to commands",
    "validate": _command_method_validate, "example": "NOTICE"})
@utils.export("channelset", {"setting": "command-method",
    "help": "Set the method used to respond to commands",
    "validate": _command_method_validate, "example": "NOTICE"})
@utils.export("channelset", {"setting": "hide-prefix",
    "help": "Disable/enable hiding prefix in command reponses",
    "validate": utils.bool_or_none, "example": "on"})
@utils.export("channelset", {"setting": "commands",
    "help": "Disable/enable responding to commands in-channel",
    "validate": utils.bool_or_none, "example": "on"})
@utils.export("channelset", {"setting": "prefixed-commands",
    "help": "Disable/enable responding to prefixed commands in-channel",
    "validate": utils.bool_or_none, "example": "on"})
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
    def get_hooks(self, command):
        return self.events.on("received.command").on(command
            ).get_hooks()

    def is_highlight(self, server, s):
        if s and s[-1] in [":", ","]:
            s = s[:-1]
        return server.is_own_nickname(s)

    def _get_aliases(self, server):
        return server.get_setting("command-aliases", {})
    def _set_aliases(self, server, aliases):
        server.set_setting("command-aliases", aliases)

    def _alias_arg_replace(self, s, args_split):
        for match in REGEX_ARG_NUMBER.finditer(s):
            index = int(match.group(1))
            continuous = match.group(2) == "-"

            if index >= len(args_split):
                raise IndexError("Unknown alias arg index")

            if continuous:
                replace = " ".join(args_split[index:])
            else:
                replace = args_split[index]
            s = s.replace(match.group(0), replace)
        return s.split(" ")

    def _command_method(self, target, server):
        return target.get_setting(COMMAND_METHOD,
            server.get_setting(COMMAND_METHOD, "PRIVMSG")).upper()

    def _find_command_hook(self, server, command, is_channel, args_split):
        if not self.has_command(command):
            aliases = self._get_aliases(server)
            if command.lower() in aliases:
                command, _, new_args = aliases[command.lower()].partition(" ")

                try:
                    args_split = self._alias_arg_replace(new_args, args_split)
                except IndexError:
                    return None, None

        hook = None
        if self.has_command(command):
            for potential_hook in self.get_hooks(command):
                alias_of = self._get_alias_of(potential_hook)
                if alias_of:
                    if self.has_command(alias_of):
                        potential_hook = self.get_hooks(alias_of)[0]
                    else:
                        raise ValueError(
                            "'%s' is an alias of unknown command '%s'"
                           % (command.lower(), alias_of.lower()))

                if not is_channel and potential_hook.kwargs.get("channel_only"):
                    continue
                if is_channel and potential_hook.kwargs.get("private_only"):
                    continue

                hook = potential_hook
                break

        return hook, args_split

    def _check(self, context, kwargs, requests=[]):
        event_hook = self.events.on(context).on("command")

        returns = []
        if requests:
            for request, request_args in requests:
                returns.append(event_hook.on(request).call_unsafe_for_result(
                    **kwargs, request_args=request_args))
        else:
            returns = event_hook.call_unsafe(**kwargs)

        hard_fail = False
        force_success = False
        error = None
        for returned in returns:
            if returned == utils.consts.PERMISSION_HARD_FAIL:
                hard_fail = True
                break
            elif returned == utils.consts.PERMISSION_FORCE_SUCCESS:
                force_success = True
            elif returned:
                error = returned

        if hard_fail:
            return False, None
        elif not force_success and error:
            return False, error
        else:
            return True, None


    def _check_assert(self, check_kwargs,
            check: typing.Union[utils.Check, utils.MultiCheck]):
        checks = check.to_multi() # both Check and MultiCheck has this func
        is_success, message = self._check("check", check_kwargs,
            checks.requests())
        if not is_success:
            raise utils.EventError(message)

    def command(self, server, target, target_str, is_channel, user, command,
            args_split, tags, hook, **kwargs):
        message_tags = server.has_capability(MESSAGE_TAGS_CAP)
        expect_output = hook.kwargs.get("expect_output", True)

        module_name = self._get_prefix(hook) or ""
        if not module_name and hasattr(hook.function, "__self__"):
            module_name = hook.function.__self__._name

        send_tags = {}
        if message_tags:
            msgid = MSGID_TAG.get_value(tags)
            if msgid:
                send_tags["+draft/reply"] = msgid

            if expect_output:
                server.send(utils.irc.protocol.tagmsg(target_str,
                    {"+draft/typing": "active"}), immediate=True)

        stdout = outs.StdOut(server, module_name, target, target_str, send_tags)
        stderr = outs.StdErr(server, module_name, target, target_str, send_tags)
        command_method = self._command_method(target, server)

        ret = False
        had_out = False

        if hook.kwargs.get("remove_empty", True):
            args_split = list(filter(None, args_split))

        min_args = hook.kwargs.get("min_args")
        if min_args and len(args_split) < min_args:
            command_prefix = ""
            if is_channel:
                command_prefix = self._command_prefix(server, target)
            usage = self._get_usage(hook, command, command_prefix)
            if usage:
                stderr.write("Not enough arguments, usage: %s" %
                    usage).send(command_method)
            else:
                stderr.write("Not enough arguments (minimum: %d)" %
                    min_args).send(command_method)
        else:
            event_kwargs = {"hook": hook, "user": user, "server": server,
                "target": target, "is_channel": is_channel, "tags": tags,
                "args_split": args_split, "command": command,
                "args": " ".join(args_split), "stdout": stdout,
                "stderr": stderr}
            event_kwargs.update(kwargs)

            check_assert = lambda check: self._check_assert(event_kwargs, check)
            event_kwargs["check_assert"] = check_assert

            check_success, check_message = self._check("preprocess",
                event_kwargs)
            if not check_success:
                if check_message:
                    stderr.write(check_message).send(command_method)
                return True

            new_event = self.events.on(hook.event_name).make_event(
                **event_kwargs)

            self.log.trace("calling command '%s': %s",
                [command, new_event.kwargs])

            try:
                hook.call(new_event)
            except utils.EventError as e:
                stderr.write(str(e)).send(command_method)
                return True

            if not hook.kwargs.get("skip_out", False):
                had_out = stdout.has_text() or stderr.has_text()
                command_method = self._command_method(target, server)
                stdout.send(command_method)
                stderr.send(command_method)
                target.last_stdout = stdout
                target.last_stderr = stderr
            ret = new_event.eaten

        if expect_output and message_tags and not had_out:
            server.send(utils.irc.protocol.tagmsg(target_str,
                {"+draft/typing": "done"}), immediate=True)

        return ret

    def _command_prefix(self, server, channel):
        return channel.get_setting("command-prefix",
            server.get_setting("command-prefix", "!"))

    @utils.hook("received.message.channel", priority=EventManager.PRIORITY_LOW)
    def channel_message(self, event):
        commands_enabled = event["channel"].get_setting("commands", True)
        if not commands_enabled:
            return

        command_prefix = self._command_prefix(event["server"], event["channel"])
        command = None
        args_split = None
        if event["message_split"][0].startswith(command_prefix):
            if not event["channel"].get_setting("prefixed-commands",True):
                return
            command = event["message_split"][0].replace(
                command_prefix, "", 1).lower()
            args_split = event["message_split"][1:]
        elif len(event["message_split"]) > 1 and self.is_highlight(
                event["server"], event["message_split"][0]):
            command = event["message_split"][1].lower()
            args_split = event["message_split"][2:]

        if command:
            if event["action"]:
                return

            hook, args_split = self._find_command_hook(event["server"], command,
                True, args_split)
            if hook:
                self.command(event["server"], event["channel"],
                    event["target_str"], True, event["user"], command,
                    args_split, event["tags"], hook,
                    command_prefix=command_prefix)
                event["channel"].buffer.skip_next()
        else:
            regex_hooks = self.events.on("command.regex").get_hooks()
            for hook in regex_hooks:
                if event["action"] and hook.get_kwarg("ignore_action", True):
                    continue

                pattern = hook.get_kwarg("pattern", None)
                if not pattern and hook.get_kwarg("pattern-url", None) == "1":
                    pattern = utils.http.REGEX_URL

                if pattern:
                    match = re.search(pattern, event["message"])
                    if match:
                        command = hook.get_kwarg("command", "")
                        res = self.command(event["server"], event["channel"],
                            event["target_str"], True, event["user"], command,
                            "", event["tags"], hook, match=match,
                            message=event["message"], command_prefix="")

                        if res:
                            break

    @utils.hook("received.message.private", priority=EventManager.PRIORITY_LOW)
    def private_message(self, event):
        if event["message_split"] and not event["action"]:
            command = event["message_split"][0].lower()

            # this should help catch commands when people try to do prefixed
            # commands ('!help' rather than 'help') in PM
            command = command.lstrip("".join(NON_ALPHANUMERIC))

            args_split = event["message_split"][1:]

            hook, args_split = self._find_command_hook(event["server"], command,
                False, args_split)

            if hook:
                self.command(event["server"], event["user"],
                    event["user"].nickname, False, event["user"], command,
                    args_split, event["tags"], hook, command_prefix="")
                event["user"].buffer.skip_next()

    def _get_usage(self, hook, command, command_prefix=""):
        command = "%s%s" % (command_prefix, command)
        usage = hook.get_kwarg("usage", None)
        if usage:
            usages = [usage]
        else:
            usages = hook.docstring.var_items.get("usage", None)

        if usages:
            return " | ".join(
                "%s %s" % (command, usage) for usage in usages)
        return usage

    def _get_prefix(self, hook):
        return hook.get_kwarg("prefix", None)
    def _get_alias_of(self, hook):
        return hook.get_kwarg("alias_of", None)

    @utils.hook("received.command.more", skip_out=True)
    def more(self, event):
        """
        :help: Show more output from the last command
        """
        if event["target"].last_stdout and event["target"].last_stdout.has_text():
            event["target"].last_stdout.send(
                self._command_method(event["target"], event["server"]))

    @utils.hook("send.stdout")
    def send_stdout(self, event):
        target = event["target"]
        stdout = outs.StdOut(event["server"], event["module_name"],
            target, event.get("target_str", target.name), {})

        if event.get("hide_prefix", False):
            stdout.hide_prefix()

        stdout.write(event["message"]).send(
            self._command_method(event["target"], event["server"]))
        if stdout.has_text():
            event["target"].last_stdout = stdout
    @utils.hook("send.stderr")
    def send_stderr(self, event):
        target = event["target"]
        stderr = outs.StdErr(event["server"], event["module_name"],
            target, event.get("target_str", target.name), {})

        if event.get("hide_prefix", False):
            stderr.hide_prefix()

        stderr.write(event["message"]).send(
            self._command_method(event["target"], event["server"]))
        if stderr.has_text():
            event["target"].last_stderr = stderr

    @utils.hook("received.command.alias", min_args=2)
    def add_alias(self, event):
        """
        :help: Add a command alias
        :usage: <alias> <command> <args...>
        :permission: command-alias
        """
        alias = event["args_split"][0].lower()
        command = " ".join(event["args_split"][1:])
        aliases = self._get_aliases(event["server"])
        aliases[alias] = command
        self._set_aliases(event["server"], aliases)
        event["stdout"].write("Added '%s' alias" % alias)

    @utils.hook("received.command.removealias", min_args=1)
    def remove_alias(self, event):
        """
        :help: Remove a command alias
        :usage: <alias>
        :permission: command-alias
        """
        alias = event["args_split"][0].lower()
        aliases = self._get_aliases(event["server"])

        if not alias in aliases:
            raise utils.EventError("No '%s' alias" % alias)

        del aliases[alias]
        self._set_aliases(event["server"], aliases)
        event["stdout"].write("Removed '%s' alias" % alias)

    @utils.hook("check.command.self")
    def check_command_self(self, event):
        if event["server"].irc_lower(event["request_args"][0]
                ) == event["user"].name:
            return utils.consts.PERMISSION_FORCE_SUCCESS
        else:
            return "You do not have permission to do this"
