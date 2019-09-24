#--depends-on channel_access
#--depends-on check_mode
#--depends-on commands
#--depends-on config

from src import ModuleManager, utils

KICK_REASON = "your behavior is not conducive to the desired environment"

KICK_REASON_SETTING = utils.Setting("default-kick-reason",
    "Set the default kick reason", example="have a nice trip")

@utils.export("channelset", utils.Setting("ban-format",
    "Set ban format ($n = nick, $u = username, $h = hostname, $a = account)",
    example="*!$u@$h"))
@utils.export("channelset", utils.Setting("ban-format-account",
    "Set ban format for users with accounts ($a = account)", example="~a:$a"))

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
        mask_split = s.split("$$")
        for i, mask_part in enumerate(mask_split):
            mask_split[i] = (s.replace("$n", user.nickname)
                .replace("$u", user.username)
                .replace("$h", user.hostname)
                .replace("$a", user.get_identified_account() or ""))
        return "$".join(mask_split)
    def _get_hostmask(self, channel, user):
        if not user.get_identified_account() == None:
            account_format = channel.get_setting("ban-format-account", None)
            if not account_format == None:
                return self._format_hostmask(user, account_format)

        format = channel.get_setting("ban-format", "*!$u@$h")
        return self._format_hostmask(user, format)

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
    @utils.hook("received.command.b", alias_of="ban")
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
        add = event["command"] == "op"
        target = event["args_split"][0] if event["args"] else event[
            "user"].nickname
        event["target"].send_mode("+o" if add else "-o", [target])

    @utils.hook("received.command.voice")
    @utils.hook("received.command.devoice")
    @utils.kwarg("channel_only", True)
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "voice")
    @utils.kwarg("usage", "[nickname]")
    def voice(self, event):
        add = event["command"] == "voice"
        target = event["args_split"][0] if event["args"] else event[
            "user"].nickname
        event["target"].send_mode("+v" if add else "-v", [target])

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

    def _mute_method(self, server, channel, user):
        mask = self._get_hostmask(channel, user)
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
        add = event["command"] == "mute"
        time, args = self._parse_time(event["args_split"], 1)

        target_name = args[0]
        if not event["server"].has_user(target_name):
            raise utils.EventError("No such user")

        target_user = event["server"].get_user(target_name)
        if not event["target"].has_user(target_user):
            raise utils.EventError("No such user")

        mode, mask = self._mute_method(event["server"], event["target"],
            target_user)
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

    @utils.hook("received.command.invite")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("channel_only", True)
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "invite")
    @utils.kwarg("help", "Invite a given user")
    @utils.kwarg("usage", "<nickname>")
    def invite(self, event):
        user_nickname = event["args_split"][0]

        event["target"].send_invite(user_nickname)

        user = event["server"].get_user(user_nickname, create=False)
        if user:
            user_nickname = user.nickname

        event["stdout"].write("Invited %s" % user_nickname)

    def _parse_flags(self, s):
        if s[0] == "+":
            return True, list(s[1:])
        elif s[0] == "-":
            return False, list(s[1:])
        else:
            return None, None

    @utils.hook("received.command.flags")
    @utils.kwarg("channel_only", True)
    @utils.kwarg("min_args", 1)
    @utils.kwarg("help", "Configure access flags for a given user")
    @utils.kwarg("usage", "<nickname> [flags]")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "flags")
    def flags(self, event):
        target = event["server"].get_user(event["args_split"][0])
        current_flags = event["target"].get_user_setting(target.get_id(),
            "flags", "")

        if len(event["args_split"]) == 1:
            current_flags_str = ("+%s" % current_flags) if current_flags else ""
            event["stdout"].write("Flags for %s: %s" % (target.nickname,
                current_flags_str))
        else:
            is_add, parsed_flags = self._parse_flags(event["args_split"][1])
            new_flags = None

            if is_add == None:
                raise utils.EventError("Invalid flags format")
            elif is_add:
                new_flags = list(set(list(current_flags)+parsed_flags))
            else:
                new_flags = list(set(current_flags)-set(parsed_flags))

            if new_flags:
                # sort alphanumeric with uppercase after lowercase
                new_flags = sorted(new_flags,
                    key=lambda c: ("0" if c.islower() else "1")+c)

                new_flags_str = "".join(new_flags)
                event["target"].set_user_setting(target.get_id(), "flags",
                    new_flags_str)

                self._check_flags(event["target"], target)

                event["stdout"].write("Set flags for %s to +%s" % (
                    target.nickname, new_flags_str))
            else:
                event["target"].del_user_setting(target.get_id(), "flags")
                event["stdout"].write("Cleared flags for %s" % target.nickname)

    def _chunk(self, l, n):
        return [l[i:i+n] for i in range(0, len(l), n)]

    @utils.hook("received.join")
    def on_join(self, event):
        self._check_flags(event["channel"], event["user"])
    @utils.hook("received.account.login")
    @utils.hook("internal.identified")
    def on_account(self, event):
        for channel in event["user"].channels:
            self._check_flags(channel, event["user"])

    def _check_flags(self, channel, user):
        flags = channel.get_user_setting(user.get_id(), "flags", "")

        if flags:
            identified = not user.get_identified_account() == None
            current_modes = channel.get_user_modes(user)

            modes = []
            kick_reason = None
            for flag in list(flags):
                if flag == "O" and identified:
                    modes.append(("o", user.nickname))
                elif flag == "V" and identified:
                    modes.append(("v", user.nickname))
                elif flag == "b":
                    modes.append(("b", self._get_hostmask(channel, user)))
                    kick_reason = "User is banned from this channel"

            new_modes = []
            for mode, arg in modes:
                if not mode in current_modes:
                    new_modes.append((mode, arg))

            # break up in to chunks of (maximum) 3
            # https://tools.ietf.org/html/rfc2812.html#section-3.2.3
            for chunk in self._chunk(new_modes, 3):
                chars, args = list(zip(*chunk))
                channel.send_mode("+%s" % "".join(chars), list(args))
            if not kick_reason == None:
                channel.send_kick(user.nickname, kick_reason)
