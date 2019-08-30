#--depends-on channel_access
#--depends-on check_mode
#--depends-on commands
#--depends-on config

from src import ModuleManager, utils

KICK_REASON = "your behavior is not conducive to the desired environment"

KICK_REASON_SETTING = utils.Setting("default-kick-reason",
    "Set the default kick reason", example="have a nice trip")

@utils.export("channelset", utils.Setting("ban-format",
    "Set ban format ($n = nick, $u = username, $h = hostname)",
    example="*!$u@$h"))
@utils.export("serverset", utils.OptionsSetting(
    ["qmode", "insp", "unreal", "none"], "mute-method",
    "Set this server's method of muting users"))
@utils.export("botset", KICK_REASON_SETTING)
@utils.export("serverset", KICK_REASON_SETTING)
@utils.export("channelset", KICK_REASON_SETTING)
class Module(ModuleManager.BaseModule):
    _name = "ChanOp"

    def _parse_time(self, args, min_args):
        if args[0][0] == "+":
            if len(args[1:]) < min_args:
                raise utils.EventError("Not enough arguments")
            time = utils.from_pretty_time(args[0][1:])
            if time == None:
                raise utils.EventError("Invalid timeframe")
            return time, args[1:]
        return None, args

    def _kick_reason(self, server, channel):
        return channel.get_setting("default-kick-reason",
            server.get_setting("default-kick-reason",
            self.bot.get_setting("default-kick-reson", KICK_REASON)))

    def _kick(self, server, channel, target_nickname, reason):
        target_user = server.get_user(target_nickname, create=False)
        if target_user and channel.has_user(target_user):
            reason = " ".join(reason) or self._kick_reason(server, channel)
            channel.send_kick(target_user.nickname, reason)
        else:
            raise utils.EventError("No such user")

    @utils.hook("received.command.kick")
    @utils.hook("received.command.k", alias_of="k")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "kick")
    @utils.kwarg("usage", "<nickname> [reason]")
    def kick(self, event):
        self._kick(event["server"], event["target"], event["args_split"][0],
            event["args_split"][1:])

    def _format_hostmask(self, user, s):
        return s.replace("$n", user.nickname).replace("$u", user.username
            ).replace("$h", user.hostname)
    def _get_hostmask(self, channel, user):
        format = channel.get_setting("ban-format", "*!$u@$h")
        hostmask_split = [
            self._format_hostmask(user, s) for s in format.split("$$")]
        return "$".join(hostmask_split)

    def _ban(self, server, channel, target, allow_hostmask, time, add):
        hostmask = None
        target_user = server.get_user(target, create=False)
        if target_user and channel.has_user(target_user):
            hostmask = self._get_hostmask(channel, target_user)
        else:
            if not allow_hostmask:
                raise utils.EventError("No such user")
            hostmask = target
        if not add:
            channel.send_unban(hostmask)
        else:
            channel.send_ban(hostmask)

            if not time == None:
                self.timers.add_persistent("unban", time, server_id=server.id,
                    channel_name=channel.name, hostmask=hostmask)

    @utils.hook("timer.unban")
    def _timer_unban(self, event):
        server = self.bot.get_server_by_id(event["server_id"])
        if server and event["channel_name"] in server.channels:
            channel = server.channels.get(event["channel_name"])
            channel.send_unban(event["hostmask"])

    @utils.hook("received.command.ban")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "ban")
    @utils.kwarg("usage", "[+time] <target>")
    def ban(self, event):
        time, args = self._parse_time(event["args_split"], 1)
        self._ban(event["server"], event["target"], args[0], True, time, True)

    @utils.hook("received.command.unban")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "ban")
    @utils.kwarg("usage", "<target>")
    def unban(self, event):
        self._ban(event["server"], event["target"], event["args_split"][0],
            True, None, False)

    @utils.hook("received.command.kickban")
    @utils.hook("received.command.kb", alias_of="kickban")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "kickban")
    @utils.kwarg("usage", "[+time] <nickname> [reason]")
    def kickban(self, event):
        time, args = self._parse_time(event["args_split"], 1)
        self._ban(event["server"], event["target"], args[0], False, time, True)
        self._kick(event["server"], event["target"], args[0], args[1:])

    @utils.hook("received.command.op")
    @utils.hook("received.command.deop")
    @utils.kwarg("channel_only", True)
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "op")
    @utils.kwarg("usage", "[nickname]")
    def op(self, event):
        add = event.name == "received.command.op"
        target = event["args_split"][0] if event["args"] else event[
            "user"].nickname
        event["target"].send_mode("+o" if add else "-o", target)

    @utils.hook("received.command.voice")
    @utils.hook("received.command.devoice")
    @utils.kwarg("channel_only", True)
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "voice")
    @utils.kwarg("usage", "[nickname]")
    def voice(self, event):
        add = event.name == "received.command.voice"
        target = event["args_split"][0] if event["args"] else event[
            "user"].nickname
        event["target"].send_mode("+v" if add else "-v", target)

    @utils.hook("received.command.topic")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("channel_only", True)
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "topic")
    @utils.kwarg("remove_empty", False)
    @utils.kwarg("usage", "<topic>")
    def topic(self, event):
        event["target"].send_topic(event["args"])

    @utils.hook("received.command.tappend")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("channel_only", True)
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "topic")
    @utils.kwarg("remove_empty", False)
    @utils.kwarg("usage", "<topic>")
    def tappend(self, event):
        event["target"].send_topic(event["target"].topic + event["args"])

    def _mute_method(self, server, user):
        mask = "*!*@%s" % user.hostname
        mute_method = server.get_setting("mute-method", "qmode").lower()

        if mute_method == "qmode":
            return "q", mask
        elif mute_method == "insp":
            return "b", "m:%s" % mask
        elif mute_method == "unreal":
            return "b", "~q:%s" % mask
        elif mute_method == "none":
            return None, None
        raise ValueError("Unknown mute-method '%s'" % mute_method)

    @utils.hook("received.command.mute", usage="[+time] <nickname>")
    @utils.hook("received.command.unmute", usage="<nickname>")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("channel_only", True)
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "mute")
    @utils.kwarg("help", "Mute a given user")
    def _mute(self, event):
        add = event.name == "received.command.mute"
        time, args = self._parse_time(event["args_split"], 1)

        target_name = args[0]
        if not event["server"].has_user(target_name):
            raise utils.EventError("No such user")

        target_user = event["server"].get_user(target_name)
        if not event["target"].has_user(target_user):
            raise utils.EventError("No such user")

        mode, mask = self._mute_method(event["server"], target_user)
        if mode == None:
            raise utils.EventError("This network doesn't support mutes")

        if add and time:
            self.timers.add_persistent("unmute", time,
                server_id=event["server"].id, channel_name=event["target"].name,
                mode=mode, mask=mask)

        mode_modifier = "+" if add else "-"
        event["target"].send_mode("%s%s" % (mode_modifier, mode), [mask])

    @utils.hook("timer.unmute")
    def _timer_unmute(self, event):
        server = self.bot.get_server_by_id(event["server_id"])
        if server and event["channel_name"] in server.channels:
            channel = server.channels.get(event["channel_name"])
            channel.send_mode("-%s" % event["mode"], [event["mask"]])
