#--depends-on config

import enum, re, shlex, string, traceback, typing
from src import EventManager, IRCLine, ModuleManager, utils
from . import outs

COMMAND_METHOD = "command-method"
COMMAND_METHODS = ["PRIVMSG", "NOTICE"]

STR_MORE = " (more...)"
STR_CONTINUED = "(...continued) "
STR_MORE_LEN = len(STR_MORE.encode("utf8"))
WORD_BOUNDARIES = [" "]

NON_ALPHANUMERIC = [char for char in string.printable if not char.isalnum()]

class OutType(enum.Enum):
    OUT = 1
    ERR = 2

class BadContextException(Exception):
    def __init__(self, required_context):
        self.required_context = required_context
        Exception.__init__(self)

class CommandEvent(object):
    def __init__(self, command, args):
        self.command = command
        self.args = args

SETTING_COMMANDMETHOD = utils.OptionsSetting(COMMAND_METHODS, COMMAND_METHOD,
    "Set the method used to respond to commands")

@utils.export("channelset", utils.Setting("command-prefix",
    "Set the command prefix used in this channel", example="!"))
@utils.export("serverset", utils.Setting("command-prefix",
    "Set the command prefix used on this server", example="!"))
@utils.export("botset", SETTING_COMMANDMETHOD)
@utils.export("serverset", SETTING_COMMANDMETHOD)
@utils.export("channelset", SETTING_COMMANDMETHOD)
@utils.export("set", SETTING_COMMANDMETHOD)
@utils.export("channelset", utils.BoolSetting("hide-prefix",
    "Disable/enable hiding prefix in command reponses"))
@utils.export("channelset", utils.BoolSetting("commands",
    "Disable/enable responding to commands in-channel"))
@utils.export("channelset", utils.BoolSetting("prefixed-commands",
    "Disable/enable responding to prefixed commands in-channel"))
class Module(ModuleManager.BaseModule):
    @utils.hook("new.user")
    @utils.hook("new.channel")
    def new(self, event):
        if "user" in event:
            target = event["user"]
        else:
            target = event["channel"]

    def has_command(self, command):
        return command.lower() in self.events.on("received").on(
            "command").get_children()
    def get_hooks(self, command):
        return self.events.on("received.command").on(command
            ).get_hooks()

    def is_highlight(self, server, s):
        if s and s[-1] in [":", ","]:
            return server.is_own_nickname(s[:-1])

    def _command_method(self, server, target, is_channel):
        default = "PRIVMSG" if is_channel else "NOTICE"

        return target.get_setting(COMMAND_METHOD,
            server.get_setting(COMMAND_METHOD,
            self.bot.get_setting(COMMAND_METHOD, default))).upper()

    def _find_command_hook(self, server, target, is_channel, command, user,
            command_prefix, args):
        if not self.has_command(command):
            command_event = CommandEvent(command, args)
            self.events.on("get.command").call(command=command_event,
                server=server, target=target, is_channel=is_channel, user=user,
                command_prefix=command_prefix, kwargs={})

            command = command_event.command
            args = command_event.args

        hook = None
        args_split = []
        channel_skip = False
        private_skip = False
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

                if not is_channel and potential_hook.get_kwarg("channel_only",
                        False):
                    channel_skip = True
                    continue
                if is_channel and potential_hook.get_kwarg("private_only",
                        False):
                    private_skip = True
                    continue

                hook = potential_hook

                if args:
                    argparse = hook.get_kwarg("argparse", "plain")
                    if argparse == "shlex":
                        args_split = shlex.split(args)
                    elif argparse == "plain":
                        args_split = args.split(" ")

                break

        if not hook and (private_skip or channel_skip):
            raise BadContextException("channel" if channel_skip else "private")

        return hook, command, args_split

    def _check(self, context, kwargs, requests=[]):
        event_hook = self.events.on(context).on("command")

        returns = []
        if requests:
            for request, request_args in requests:
                returns.append(event_hook.on(request).call_for_result_unsafe(
                    **kwargs, request_args=request_args))
        else:
            returns = event_hook.call_unsafe(**kwargs)

        hard_fail = False
        force_success = False
        error = None
        for returned in returns:
            if returned:
                type, message = returned
                if type == utils.consts.PERMISSION_HARD_FAIL:
                    error = message
                    hard_fail = True
                    break
                elif type == utils.consts.PERMISSION_FORCE_SUCCESS:
                    force_success = True
                    break
                elif type == utils.consts.PERMISSION_ERROR:
                    error = message

        if hard_fail:
            return False, error
        elif not force_success and error:
            return False, error
        else:
            return True, None


    def _check_assert(self, check_kwargs, user,
            check: typing.Union[utils.Check, utils.MultiCheck]):
        checks = check.to_multi() # both Check and MultiCheck has this func
        is_success, message = self._check("check", check_kwargs,
            checks.requests())
        if not is_success:
            raise utils.EventError("%s: %s" % (user.nickname, message))

    def command(self, server, target, target_str, is_channel, user, command,
            args_split, line, hook, **kwargs):
        module_name = (self._get_prefix(hook) or
            self.bot.modules.from_context(hook.context).title)

        stdout = outs.StdOut(module_name)
        stderr = outs.StdOut(module_name)

        ret = False
        has_out = False

        if hook.get_kwarg("remove_empty", True):
            args_split = list(filter(None, args_split))

        event_kwargs = {"hook": hook, "user": user, "server": server,
            "target": target, "target_str": target_str,
            "is_channel": is_channel, "line": line, "args_split": args_split,
            "command": command, "args": " ".join(args_split), "stdout": stdout,
            "stderr": stderr, "tags": {}, "kwargs": {}}

        event_kwargs.update(kwargs)

        check_assert = lambda check: self._check_assert(event_kwargs, user,
            check)
        event_kwargs["check_assert"] = check_assert

        eaten = False

        check_success, check_message = self._check("preprocess", event_kwargs)
        if check_success:
            event_kwargs.update(event_kwargs.pop("kwargs"))
            new_event = self.events.on(hook.event_name).make_event(**event_kwargs)
            self.log.trace("calling command '%s': %s", [command, new_event.kwargs])

            try:
                hook.call(new_event)
            except utils.EventError as e:
                stderr.write(str(e))
            eaten = new_event.eaten
        else:
            if check_message:
                stderr.write("%s: %s" % (user.nickname, check_message))

        self._check("postprocess", event_kwargs)
        # postprocess - send stdout/stderr and typing tag

        return eaten

    @utils.hook("postprocess.command")
    @utils.kwarg("priority", EventManager.PRIORITY_LOW)
    def postprocess(self, event):
        type = None
        obj = None
        if event["stdout"].has_text():
            type = OutType.OUT
            obj = event["stdout"]
        elif event["stderr"].has_text():
            type = OutType.ERR
            obj = event["stderr"]
        else:
            return
        self._out(event["server"], event["target"], event["target_str"],
            event["is_channel"], obj, type, event["tags"])

    def _out(self, server, target, target_str, is_channel, obj, type, tags):
        if type == OutType.OUT:
            color = utils.consts.GREEN
        else:
            color = utils.consts.RED

        line_str = obj.pop()
        prefix = ""
        if obj.prefix:
            prefix = "[%s] " % utils.irc.color(obj.prefix, color)
            if obj._overflowed:
                prefix = "%s%s" % (prefix, STR_CONTINUED)
        method = self._command_method(server, target, is_channel)

        if not method in ["PRIVMSG", "NOTICE"]:
            raise ValueError("Unknown command-method '%s'" % method)

        line = server.new_line(method, [target_str, prefix], tags=tags)

        overflow = line.push_last(line_str, human_trunc=True,
            extra_margin=STR_MORE_LEN)
        if overflow:
            line.push_last(STR_MORE)
            obj.insert(overflow)
            obj._overflowed = True

        if obj._assured:
            line.assure()
        server.send(line)

    @utils.hook("preprocess.command")
    def _check_min_args(self, event):
        min_args = event["hook"].get_kwarg("min_args")
        if min_args and len(event["args_split"]) < min_args:
            usage = self._get_usage(event["hook"], event["command"],
                event["command_prefix"])
            error = None
            if usage:
                error = "Not enough arguments, usage: %s" % usage
            else:
                error = "Not enough arguments (minimum: %d)" % min_args
            return utils.consts.PERMISSION_HARD_FAIL, error

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
        args = ""
        if event["message_split"][0].startswith(command_prefix):
            if not event["channel"].get_setting("prefixed-commands",True):
                return
            command = event["message_split"][0].replace(
                command_prefix, "", 1).lower()
            if " " in event["message"]:
                args = event["message"].split(" ", 1)[1]
        elif len(event["message_split"]) > 1 and self.is_highlight(
                event["server"], event["message_split"][0]):
            command = event["message_split"][1].lower()
            if event["message"].count(" ") > 1:
                args = event["message"].split(" ", 2)[2]

        hook = None
        args_split = []
        if command:
            try:
                hook, command, args_split = self._find_command_hook(
                    event["server"], event["channel"], True, command,
                    event["user"], command_prefix, args)
            except BadContextException:
                event["channel"].send_message(
                    "%s: That command is not valid in a channel" %
                    event["user"].nickname)
                return

        if hook:
            if event["action"]:
                return

            if hook:
                self.command(event["server"], event["channel"],
                    event["target_str"], True, event["user"], command,
                    args_split, event["line"], hook,
                    command_prefix=command_prefix, expect_output=True,
                    buffer_line=event["buffer_line"])
            else:
                self.events.on("unknown.command").call(server=event["server"],
                    target=event["channel"], user=event["user"],
                    command=command, command_prefix=command_prefix,
                    is_channel=True)
        else:
            regex_hooks = self.events.on("command.regex").get_hooks()
            for hook in regex_hooks:
                if event["action"] and hook.get_kwarg("ignore_action", True):
                    continue
                if event["statusmsg"] and not hook.get_kwarg("statusmsg", False
                        ):
                    continue

                pattern = hook.get_kwarg("pattern", None)
                if pattern:
                    match = re.search(pattern, event["message"])
                    if match:
                        command = hook.get_kwarg("command", "")
                        res = self.command(event["server"], event["channel"],
                            event["target_str"], True, event["user"], command,
                            "", event["line"], hook, match=match,
                            message=event["message"], command_prefix="",
                            action=event["action"], expect_output=False,
                            buffer_line=event["buffer_line"])

                        if res:
                            break

    @utils.hook("received.message.private", priority=EventManager.PRIORITY_LOW)
    def private_message(self, event):
        if event["message_split"] and not event["action"]:
            command = event["message_split"][0].lower()

            # this should help catch commands when people try to do prefixed
            # commands ('!help' rather than 'help') in PM
            command = command.lstrip("".join(NON_ALPHANUMERIC))

            args = ""
            if " " in event["message"]:
                args = event["message"].split(" ", 1)[1]

            try:
                hook, command, args_split = self._find_command_hook(
                    event["server"], event["user"], False, command,
                    event["user"], "", args)
            except BadContextException:
                event["user"].send_message(
                    "That command is not valid in a PM")
                return

            if hook:
                self.command(event["server"], event["user"],
                    event["user"].nickname, False, event["user"], command,
                    args_split, event["line"], hook, command_prefix="",
                    buffer_line=event["buffer_line"], expect_output=True)
            else:
                self.events.on("unknown.command").call(server=event["server"],
                    target=event["user"], user=event["user"], command=command,
                    command_prefix="", is_channel=False)

    def _get_usage(self, hook, command, command_prefix=""):
        command = "%s%s" % (command_prefix, command)
        usages = hook.get_kwargs("usage")

        if usages:
            return " | ".join(
                "%s %s" % (command, usage) for usage in usages)
        return None

    def _get_prefix(self, hook):
        return hook.get_kwarg("prefix", None)
    def _get_alias_of(self, hook):
        return hook.get_kwarg("alias_of", None)

    @utils.hook("send.stdout")
    def _stdout(self, event):
        self._send_out(event, OutType.OUT)
    @utils.hook("send.stderr")
    def _stderr(self, event):
        self._send_out(event, OutType.ERR)

    def _send_out(self, event, type):
        target = event["target"]
        stdout = outs.StdOut(event["module_name"])
        stdout.write(event["message"])
        if event.get("hide_prefix", False):
            stdout.prefix = None

        target_str = event.get("target_str", target.name)
        self._out(event["server"], target, target_str, True, stdout, type, {})

    @utils.hook("check.command.self")
    def check_command_self(self, event):
        if event["server"].irc_lower(event["request_args"][0]
                ) == event["user"].name:
            return utils.consts.PERMISSION_FORCE_SUCCESS, None
        else:
            return (utils.consts.PERMISSION_ERROR,
                "You do not have permission to do this")

    @utils.hook("check.command.is-channel")
    def check_command_is_channel(self, event):
        if event["is_channel"]:
            return utils.consts.PERMISSION_FORCE_SUCCESS, None
        else:
            return (utils.consts.PERMISSION_ERROR,
                "This command can only be used in-channel")
