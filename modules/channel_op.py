#--depends-on channel_access
#--depends-on check_mode
#--depends-on commands
#--depends-on config

from src import ModuleManager, utils

QUIET_METHODS = {
    "qmode": ["q", "", "728", "729"],
    "insp":  ["b", "m:", "367", "368"],
    "unreal":  ["b", "~q:", "367", "368"]
}

KICK_REASON = "your behavior is not conducive to the desired environment"

NO_QUIETS = "This network doesn't support quiets"

KICK_REASON_SETTING = utils.Setting("default-kick-reason",
    "Set the default kick reason", example="have a nice trip")

@utils.export("channelset", utils.Setting("ban-format",
    "Set ban format ($n = nick, $u = username, $h = hostname, $a = account)",

    example="*!$u@$h"))
@utils.export("channelset", utils.Setting("ban-format-account",
    "Set ban format for users with accounts "
    "($n = nick, $u = username, $h = hostname, $a = account)", example="~a:$a"))

@utils.export("serverset", utils.OptionsSetting(
    list(QUIET_METHODS.keys())+["none"], "quiet-method",
    "Set this server's method of muting users"))
@utils.export("botset", KICK_REASON_SETTING)
@utils.export("serverset", KICK_REASON_SETTING)
@utils.export("channelset", KICK_REASON_SETTING)
class Module(ModuleManager.BaseModule):
    _name = "ChanOp"

    @utils.hook("timer.unmode")
    def unmode(self, timer):
        channel = self.bot.database.channels.by_id(timer.kwargs["channel"])

        if channel:
            server_id, channel_name = channel
            server = self.bot.get_server_by_id(server_id)
            if server and channel_name in server.channels:
                channel = server.channels.get(channel_name)
                mode = "-%s" % timer.kwargs.get("mode", "b")

                arg = timer.kwargs.get("args", [timer.kwargs.get("arg", None)])
                server.send_mode(channel.name, mode, arg)


    def _kick_reason(self, server, channel):
        return channel.get_setting("default-kick-reason",
            server.get_setting("default-kick-reason",
            self.bot.get_setting("default-kick-reson", KICK_REASON)))

    def _kick(self, server, channel, nicknames, reason):
        reason = reason or self._kick_reason(server, channel)
        channel.send_kicks(nicknames, reason)

    @utils.hook("received.command.kick")
    @utils.hook("received.command.k", alias_of="kick")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "high,kick")
    @utils.kwarg("help", "Kick a user from a channel")
    @utils.spec("!<#channel>r~channel !<nickname>cuser ?<reason>string")
    def kick(self, event):
        self._kick(event["server"], event["spec"][0],
            [event["spec"][1].nickname], event["spec"][2])

    def _format_hostmask(self, user, s):
        vars = {}
        vars["n"] = vars["nickname"] = user.nickname
        vars["u"] = vars["username"] = user.username
        vars["h"] = vars["hostname"] = user.hostname
        vars["a"] = vars["account"] = user.account or ""
        return utils.parse.format_token_replace(s, vars)
    def _get_hostmask(self, channel, user):
        if not user.account == None:
            account_format = channel.get_setting("ban-format-account", None)
            if not account_format == None:
                return self._format_hostmask(user, account_format)

        format = channel.get_setting("ban-format", "*!$u@$h")
        return self._format_hostmask(user, format)

    def _ban(self, channel, masks, time, add):
        if not add:
            channel.send_modes("b", False, masks)
        else:
            channel.send_modes("b", True, masks)

            if not time == None:
                self.timers.add_persistent("unmode", time, channel=channel.id,
                    args=args)

    def _mask_spec(self, channel, spec):
        if spec[0] == "cuser":
            return [self._get_hostmask(channel, spec[1])]
        elif spec[0] == "cmask":
            return [self._get_hostmask(channel, u) for u in spec[1]]
        elif spec[0] == "word":
            return [spec[1]]

    @utils.hook("received.command.ban")
    @utils.hook("received.command.b", alias_of="ban")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "high,ban")
    @utils.spec(
        "!<#channel>r~channel ?duration !<nickname>user|<mask>cmask|<mask>word")
    def ban(self, event):
        masks = self._mask_spec(event["spec"][0], event["spec"][2])
        self._ban(event["spec"][0], masks, event["spec"][1], True)

    @utils.hook("received.command.unban")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "high,ban")
    @utils.spec("!<#channel>r~channel !<nickname>user|<mask>word")
    def unban(self, event):
        if event["spec"][1][0] == "user":
            masks = self._get_hostmask(event["spec"][0], event["spec"][1][1])
        elif event["spec"][1][0] == "word":
            _, masks = self._list_query_event(event["server"],
                event["spec"][0], "+b", event["spec"][1][1])
        if masks:
            event["spec"][0].send_modes("b", False, masks)
        else:
            event["stderr"].write("No bans found to remove")

    @utils.hook("received.command.kickban")
    @utils.hook("received.command.kb", alias_of="kickban")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "high,kickban")
    @utils.spec(
        "!<#channel>r~channel ?duration "
        "!<nickname>cuser|<mask>cmask ?<reason>string")
    def kickban(self, event):
        masks = self._mask_spec(event["spec"][0], event["spec"][2])
        self._ban(event["spec"][0], masks, event["spec"][1], True)

        if event["spec"][2][0] == "cmask":
            users = event["spec"][2][1]
        else:
            users = [event["spec"][2][1]]
        self._kick(event["server"], event["spec"][0],
            [u.nickname for u in users], event["spec"][3])

    @utils.hook("received.command.op")
    @utils.hook("received.command.up", alias_of="op")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "high,op")
    @utils.spec("!<#channel>r~channel !<nickname>ruser")
    def op(self, event):
        self._op(True, event["spec"])

    @utils.hook("received.command.deop")
    @utils.hook("received.command.down", alias_of="deop")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "high,op")
    @utils.spec("!<#channel>r~channel !<nickname>ruser")
    def deop(self, event):
        self._op(False, event["spec"])

    def _op(self, add, spec):
        spec[0].send_mode("%so" % ("+" if add else "-"), [spec[1].nickname])

    @utils.hook("received.command.voice")
    @utils.hook("received.command.devoice")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "low,voice")
    @utils.spec("!<#channel>r~channel !<nickname>ruser")
    def voice(self, event):
        add = event["command"] == "voice"
        event["spec"][0].send_mode("+v" if add else "-v",
            [event["spec"][1].nickname])

    @utils.hook("received.command.topic")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "low,topic")
    @utils.kwarg("remove_empty", False)
    @utils.spec("!<#channel>r~channel !<topic>string")
    def topic(self, event):
        event["spec"][0].send_topic(event["spec"][1])

    @utils.hook("received.command.tappend")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "low,topic")
    @utils.kwarg("remove_empty", False)
    @utils.spec("!<#channel>r~channel !<topic>string")
    def tappend(self, event):
        event["spec"][0].send_topic(event["spec"][0].topic + event["spec"][1])

    def _quiet_method(self, server):
        if server.quiet:
            return server.quiet

        quiet_method = server.get_setting("quiet-method", "none").lower()

        if quiet_method in QUIET_METHODS:
            return QUIET_METHODS[quiet_method]
        elif quiet_method == "none":
            return None
        else:
            raise ValueError("Unknown quiet-method '%s'" % quiet_method)

    @utils.hook("received.command.quiet")
    @utils.hook("received.command.mute")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "high,quiet")
    @utils.kwarg("help", "Quiet a given user")
    @utils.spec("!<#channel>r~channel ?duration !<nickname>user|<mask>word")
    def quiet(self, event):
        self._quiet(event["server"], event["spec"][0], event["spec"][2], True,
            event["spec"][1])

    @utils.hook("received.command.unquiet")
    @utils.hook("received.command.unmute")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "high,unquiet")
    @utils.kwarg("help", "Unquiet a given user")
    @utils.spec("!<#channel>r~channel !<nickname>user|<mask>word")
    def unquiet(self, event):
        self._quiet(event["server"], event["spec"][0], event["spec"][1], False,
            None)

    def _quiet(self, server, channel, target, add, time):
        quiet_method = self._quiet_method(server)

        if quiet_method == None:
            raise utils.EventError(NO_QUIETS)

        mode, prefix, _, _ = quiet_method
        if target[0] == "word":
            mask = target[1]
        else:
            mask = self._get_hostmask(channel, target[1])
        mask = "%s%s" % (prefix, mask)

        if add and time:
            self.timers.add_persistent("unmode", time, channel=channel.id,
                mode=mode, arg=mask)

        mode_modifier = "+" if add else "-"
        channel.send_mode("%s%s" % (mode_modifier, mode), [mask])

    @utils.hook("received.command.invite")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "low,invite")
    @utils.kwarg("help", "Invite a given user")
    @utils.spec("!<#channel>r~channel !<nickname>word")
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
    @utils.kwarg("help", "Configure access flags for a given user")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "admin,flags")
    @utils.spec("!<#channel>r~channel !<nickname>ouser ?<flags>word")
    def flags(self, event):
        target = event["spec"][1]
        current_flags = event["spec"][0].get_user_setting(target.get_id(),
            "flags", "")

        if not event["spec"][2]:
            current_flags_str = ("+%s" % current_flags) if current_flags else ""
            event["stdout"].write("Flags for %s: %s" %
                (target, current_flags_str))
        else:
            is_add, parsed_flags = self._parse_flags(event["spec"][2])
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
                event["spec"][0].set_user_setting(target.get_id(), "flags",
                    new_flags_str)

                self._check_flags(event["server"], event["spec"][0], target)

                event["stdout"].write("Set flags for %s to +%s" % (
                    target.nickname, new_flags_str))
            else:
                event["spec"][0].del_user_setting(target.get_id(), "flags")
                event["stdout"].write("Cleared flags for %s" % target.nickname)

    def _chunk_n(self, n, l):
        return [l[i:i+n] for i in range(0, len(l), n)]
    def _chunk(self, server, l):
        # if `MODES` is not present - default to 3
        # if `MODES` is present without an arg, default to 6
        n = int(server.isupport.get("MODES", "3") or "6")
        return self._chunk_n(n, l)

    @utils.hook("received.join")
    def on_join(self, event):
        self._check_flags(event["server"], event["channel"], event["user"])
    @utils.hook("received.account.login")
    @utils.hook("internal.identified")
    def on_account(self, event):
        for channel in event["user"].channels:
            self._check_flags(event["server"], channel, event["user"])

    def _check_flags(self, server, channel, user):
        flags = channel.get_user_setting(user.get_id(), "flags", "")

        if flags:
            identified = not user._id_override == None
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
            for chunk in self._chunk(server, new_modes):
                chars, args = list(zip(*chunk))
                channel.send_mode("+%s" % "".join(chars), list(args))
            if not kick_reason == None:
                channel.send_kick(user.nickname, kick_reason)

    @utils.hook("received.command.cmute")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "high,cmute")
    @utils.kwarg("help", "Mute the current channel")
    @utils.spec("!<#channel>r~channel ?duration")
    def cmute(self, event):
        event["spec"][0].send_mode("+m")

        if event["spec"][1]:
            self.timers.add_persistent("unmode", event["spec"][1],
                channel=event["spec"][0].id, mode="m")

    @utils.hook("received.command.cunmute")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "high,cmute")
    @utils.kwarg("help", "Mute the current channel")
    @utils.spec("!<#channel>r~channel")
    def cunmute(self, event):
        self._cunmute(event["spec"][0])

    def _cunmute(self, channel):
        channel.send_mode("-m")

    def _filter_mask(self, mask, mode_list):
        parsed_mask = utils.irc.hostmask_parse(mask)
        return list(utils.irc.hostmask_match_many(mode_list, parsed_mask))
    def _filter_prefix(self, prefix, list):
        return [l for l in list if prefix in l]

    def _type_to_mode(self, server, channel, type):
        if type[0] == "+":
            if type[1:]:
                if type[1] in channel.mode_lists:
                    return type[1], None
                else:
                    raise utils.EventError("Unknown list mode")
            else:
                raise utils.EventError("Please provide a list mode")
        elif type in ["quiets", "mutes"]:
            quiet_method = self._quiet_method(server)
            if quiet_method:
                return quiet_method[0], quiet_method[1]
            else:
                raise utils.EventError(NO_QUIETS)
        else:
            raise utils.EventError("Unknown type '%s'" % type)

    def _list_query_event(self, server, channel, list_type, list_mask):
        list_mode, list_prefix = self._type_to_mode(server, channel, list_type)

        mode_list = list(channel.mode_lists[list_mode])
        if list_prefix:
            mode_list = self._filter_prefix(list_prefix, mode_list)
        if list_mask:
            mode_list = self._filter_mask(list_mask, mode_list)

        return list_mode, mode_list

    @utils.hook("received.command.clear")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "admin,clear")
    @utils.kwarg("help", "Clear a given channel list mode (e.g. +b)")
    @utils.spec("!<#channel>r~channel !<type>word|<mode>word ?<mask>word")
    def clear(self, event):
        mode, mode_list = self._list_query_event(
            event["server"], event["spec"][0], event["spec"][1],
            event["spec"][2])

        event["spec"][0].send_modes(mode, False, mode_list)

    @utils.hook("received.command.lsearch")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "high,lsearch")
    @utils.kwarg("help", "Search a given channel list mode (e.g. +b)")
    @utils.spec("!<#channel>r~channel !<type>word|<mode>word ?<mask>word")
    def lsearch(self, event):
        mode, mode_list = self._list_query_event(
            event["server"], event["spec"][0], event["spec"][1],
            event["spec"][2])

        if mode_list:
            event["stdout"].write("%s: %s" %
                (event["user"].nickname, " ".join(mode_list)))
        else:
            event["stderr"].write("%s: no matches" % event["user"].nickname)
