#--depends-on channel_access
#--depends-on check_mode
#--depends-on commands
#--depends-on config

import enum
from src import ModuleManager, utils

QUIET_METHODS = {
    "qmode":  ["q", "",    "728", "729"],
    "insp":   ["b", "m:",  "367", "368"],
    "unreal": ["b", "~q:", "367", "368"]
}
ABAN_METHODS = {
    "chary":  "$a:",
    "insp":   "R:",
    "unreal": "~a:"
}

KICK_REASON = "your behavior is not conducive to the desired environment"
NO_QUIETS = "This network doesn't support quiets"
NO_ABANS = "This network doesn't support account bans"

class TargetType(enum.Enum):
    NICKNAME = 1
    MASK = 2
    ACCOUNT = 3

def _mlock(s):
    modes, *args = s.split(" ")

    adds = ""
    removes = ""
    add = True
    for c in modes:
        if c == "+":
            add = True
        elif c == "-":
            add = False
        elif add:
            adds += c
        else:
            removes += c

    return (
        "" if not adds else f"+{''.join(adds)}",
        "" if not removes else f"-{''.join(removes)}",
        args
    )

KICK_REASON_SETTING = utils.Setting("default-kick-reason",
    "Set the default kick reason", example="have a nice trip")

BAN_FORMATTING = "${n} = nick, ${u} = username, ${h} = hostname, ${a} = account"
@utils.export("channelset", utils.Setting("ban-format",
    "Set ban format (%s)" % BAN_FORMATTING, example="*!${u}@${h}"))

@utils.export("serverset", utils.OptionsSetting(
    list(QUIET_METHODS.keys()), "quiet-method",
    "Set this server's method of muting users"))
@utils.export("serverset", utils.OptionsSetting(
    list(ABAN_METHODS.keys()), "aban-method",
    "Set this server's method of banning users by account"))

@utils.export("botset", KICK_REASON_SETTING)
@utils.export("serverset", KICK_REASON_SETTING)
@utils.export("channelset", KICK_REASON_SETTING)

@utils.export("channelset", utils.FunctionSetting(_mlock, "mlock",
    "Set which modes are locked on and off for the current channel",
    example="+mnt-z"))
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

                args = timer.kwargs.get("args", [timer.kwargs.get("arg", None)])
                if any(args):
                    channel.send_modes(args, False)
                else:
                    channel.send_mode(timer.kwargs["mode"], False)

    def _kick_reason(self, server, channel):
        return channel.get_setting("default-kick-reason",
            server.get_setting("default-kick-reason",
            self.bot.get_setting("default-kick-reson", KICK_REASON)))

    def _kick(self, server, channel, nicknames, reason):
        reason = reason or self._kick_reason(server, channel)
        channel.send_kicks(nicknames, reason)

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

        method = server.get_setting("quiet-method", None)
        return QUIET_METHODS.get(method, None)

    def _aban_method(self, server):
        method = server.get_setting("aban-method", None)
        return ABAN_METHODS.get(method, None)

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
                    mask = self.exports.get("ban-mask")(server, channel, user)
                    modes.append(("b", mask))
                    kick_reason = "User is banned from this channel"

            new_modes = []
            for mode, arg in modes:
                if not mode in current_modes:
                    new_modes.append((mode, arg))

            if new_modes:
                channel.send_modes(new_modes, True)
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
                channel=event["spec"][0].id, mode="-m")
    @utils.hook("received.command.cunmute")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "high,cmute")
    @utils.kwarg("help", "Mute the current channel")
    @utils.spec("!<#channel>r~channel")
    def cunmute(self, event):
        event["spec"][0].send_mode("-m")

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

    def _list_query_event(self, channel, list_mask, list_mode, list_prefix):
        mode_list = list(channel.mode_lists[list_mode])
        if list_prefix:
            mode_list = self._filter_prefix(list_prefix, mode_list)
        if list_mask:
            mode_list = self._filter_mask(list_mask, mode_list)

        return mode_list

    @utils.hook("received.command.clear")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "admin,clear")
    @utils.kwarg("help", "Clear a given channel list mode (e.g. +b)")
    @utils.spec("!<#channel>r~channel !<type>word|<mode>word ?<mask>word")
    def clear(self, event):
        mode, prefix = self._type_to_mode(event["server"], event["spec"][0],
            event["spec"][1])

        mode_list = self._list_query_event(event["spec"][0], event["spec"][2],
            mode, prefix)

        event["spec"][0].send_modes([(mode, a) for a in mode_list], False)

    @utils.hook("received.command.lsearch")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "high,lsearch")
    @utils.kwarg("help", "Search a given channel list mode (e.g. +b)")
    @utils.spec("!<#channel>r~channel !<type>word|<mode>word ?<mask>word")
    def lsearch(self, event):
        mode, prefix = self._type_to_mode(event["server"], event["spec"][0],
            event["spec"][1])

        mode_list = self._list_query_event(event["spec"][0], event["spec"][2],
            mode, prefix)

        if mode_list:
            event["stdout"].write("%s: %s" %
                (event["user"].nickname, " ".join(mode_list)))
        else:
            event["stderr"].write("%s: no matches" % event["user"].nickname)

    def _find_mode(self, type, server):
        if type == "ban":
            return TargetType.MASK, "b", ""
        elif type == "aban":
            aban_method = self._aban_method(server)
            if aban_method == None:
                raise utils.EventError(NO_ABANS)
            return TargetType.ACCOUNT, "b", aban_method
        elif type == "invex":
            if not "INVEX" in server.isupport:
                raise utils.EventError(
                    "invexes are not supported on this network")
            return TargetType.MASK, server.isupport["INVEX"] or "I", ""
        elif type == "quiet":
            quiet_method = self._quiet_method(server)
            if quiet_method == None:
                raise utils.EventError(NO_QUIETS)
            mode, prefix, _, _ = quiet_method
            return TargetType.MASK, mode, prefix
        elif type == "op":
            return TargetType.NICKNAME, "o", None
        elif type =="voice":
            return TargetType.NICKNAME, "v", None

    @utils.hook("received.command.ban", require_access="high,ban", type="ban")
    @utils.hook("received.command.aban", require_access="high,ban", type="aban")
    @utils.hook("received.command.quiet", require_access="high,quiet",
        type="quiet")
    @utils.hook("received.command.invex", require_access="high,invex",
        type="invex")
    @utils.kwarg("require_mode", "o")
    @utils.spec("!r~channel ?duration !<mask>cmask|<nickname>user|<mask>word")
    def mask_mode(self, event):
        self._mask_mode(event["server"], event["user"], event["spec"],
            event["hook"].get_kwarg("type"))

    @utils.hook("received.command.op", require_access="high,op", type="op")
    @utils.hook("received.command.voice", require_access="low,voice",
        type="voice")
    @utils.kwarg("require_mode", "o")
    @utils.spec("!r~channel ?duration ?<mask>cmask|<nickname>cuser")
    def access_mode(self, event):
        self._mask_mode(event["server"], event["user"], event["spec"],
            event["hook"].get_kwarg("type"))

    def _mask_kick(self, server, channel, target, reason):
        if target[0] == "cmask":
            users = target[1]
        elif target[0] == "cuser":
            users = [target[1]]

        for i, user in enumerate(users):
            if server.is_own_nickname(user.nickname):
                users.append(users.pop(i))
                break

        self._kick(server, channel, [u.nickname for u in users], reason)

    @utils.hook("received.command.kick")
    @utils.kwarg("require_access", "high,kick")
    @utils.kwarg("require_mode", "o")
    @utils.spec(
        "!r~channel !<mask>cmask|<nickname>cuser ?<reason>string")
    def kick(self, event):
        self._mask_kick(event["server"], event["spec"][0], event["spec"][1],
            event["spec"][2])

    @utils.hook("received.command.kickban", type="ban")
    @utils.hook("received.command.akickban", type="aban")
    @utils.kwarg("require_access", "high,kickban")
    @utils.kwarg("require_mode", "o")
    @utils.spec(
        "!r~channel ?duration !<mask>cmask|<nickname>cuser ?<reason>string")
    def kickban(self, event):
        self._mask_mode(event["server"], event["user"], event["spec"],
            event["hook"].get_kwarg("type"))
        self._mask_kick(event["server"], event["spec"][0], event["spec"][2],
            event["spec"][3])

    def _mask_mode(self, server, user, spec, type):
        users = args = []
        if spec[2] == None:
            users = [user]
        elif spec[2][0] == "cmask":
            users = spec[2][1]
        elif spec[2][0] in ["user", "cuser"]:
            users = [spec[2][1]]
        elif spec[2][0] == "word":
            args = [spec[2][1]]

        target_type, mode, prefix = self._find_mode(type, server)
        if users:
            if target_type == TargetType.MASK:
                mask_f = self.exports.get("ban-mask")
                args = [mask_f(server, spec[0], u) for u in users]
            elif target_type == TargetType.NICKNAME:
                args = [
                    u.nickname for u in users if not spec[0].has_umode(u, mode)]
            elif target_type == TargetType.ACCOUNT:
                args = [u.account for u in users if not u.account == None]

        if args:
            args = [(mode, "%s%s" % (prefix or "", a)) for a in args]
            spec[0].send_modes(args, True)

            if not spec[1] == None:
                self.timers.add_persistent("unmode", spec[1],
                    channel=spec[0].id, args=args)

    @utils.hook("received.command.unban", require_access="high,unban",
        type="ban")
    @utils.hook("received.command.unquiet", require_access="high,unquiet",
        type="quiet")
    @utils.hook("received.command.uninvex", require_access="high,uninvex",
        type="invex")
    @utils.kwarg("require_mode", "o")
    @utils.spec("!r~channel !<nickname>user|<mask>word")
    def mask_unmode(self, event):
        is_mask, mode, prefix = self._find_mode(
            event["hook"].get_kwarg("type"), event["server"])

        users = args = []
        if event["spec"][1][0] == "user":
            mask_f = self.exports.get("ban-mask")
            masks = [
                mask_f(event["server"], event["spec"][0], event["spec"][1][1])]
        elif event["spec"][1][0] == "word":
            masks = self._list_query_event(event["spec"][0],
                event["spec"][1][1], mode, prefix)

        if masks:
            event["spec"][0].send_modes([(mode, a) for a in masks], False)

    @utils.hook("received.command.deop", require_access="high,deop", type="op")
    @utils.hook("received.command.devoice", require_access="low,devoice",
        type="voice")
    @utils.kwarg("require_mode", "o")
    @utils.spec("!r~channel ?<nickname>cuser|<mask>cmask")
    def access_unmode(self, event):
        if event["spec"][1] == None:
            users = [event["user"]]
        elif event["spec"][1][0] == "cuser":
            users = [event["spec"][1][1]]
        elif event["spec"][1][0] == "cmask":
            users = event["spec"][1][1]

        for i, user in enumerate(users):
            if event["server"].is_own_nickname(user.nickname):
                users.append(users.pop(i))
                break

        _, mode, _ = self._find_mode(
            event["hook"].get_kwarg("type"), event["server"])
        valid_nicks = [
            u.nickname for u in users if event["spec"][0].has_umode(u, mode)]

        if valid_nicks:
            event["spec"][0].send_modes([(mode, a) for a in valid_nicks], False)

    @utils.hook("received.command.down")
    @utils.spec("!r~channel ?<nickname>cuser|<mask>cmask")
    def down(self, event):
        if not event["spec"][1] or event["spec"][1][1] == event["user"]:
            users = [event["user"]]
        else:
            event["check_assert"](
                utils.Check("channel-mode", "o")|
                utils.Check("channel-access", "high,down"))

            if event["spec"][1][0] == "cuser":
                users = [event["spec"][1][1]]
            elif event["spec"][1][0] == "cmask":
                users = event["spec"][1][1]

        for i, user in enumerate(users):
            if event["server"].is_own_nickname(user.nickname):
                users.append(users.pop(i))
                break

        modes = []
        for user in users:
            user_modes = event["spec"][0].get_user_modes(user)
            modes.extend([(m, user.nickname) for m in user_modes])

        if modes:
            event["spec"][0].send_modes(modes, False)

    @utils.hook("received.324")
    @utils.hook("received.mode.channel")
    def on_modes(self, event):
        mlock = event["channel"].get_setting("mlock", None)
        if mlock:
            changes_adds = ""
            changes_removes = ""
            changes_args = []
            adds, removes, args = mlock
            args = args.copy() # cached settings objects are mutable

            for mode in adds[1:]:
                if not event["channel"].has_mode(mode):
                    if (mode in event["server"].channel_list_modes or
                            mode in event["server"].channel_parametered_modes or
                            mode in event["server"].channel_setting_modes):
                        changes_adds += mode
                        changes_args.append(args.pop(0))
                    elif mode in event["server"].channel_modes:
                        changes_adds += mode

            for mode in removes[1:]:
                if event["channel"].has_mode(mode):
                    if (mode in event["server"].channel_list_modes or
                            mode in event["server"].channel_parametered_modes):
                        changes_removes += mode
                        changes_args.append(args.pop(0))
                    elif (mode in event["server"].channel_setting_modes or
                            mode in event["server"].channel_modes):
                        changes_removes += mode

            out = ""
            if changes_adds:
                out += f"+{changes_adds}"
            if changes_removes:
                out += f"-{changes_removes}"

            if out:
                event["channel"].send_mode(out, changes_args)
