import datetime
from src import EventManager, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _color(self, nickname):
        return utils.irc.hash_colorize(nickname)

    @utils.export("format")
    def _event(self, type, server, line, context, minimal=None, channel=None,
            user=None, formatting={}, **kwargs):
        pretty = line
        minimal = minimal or line

        if user:
            formatting["~NICK"] = formatting["NICK"] = user.nickname

        line = line.format(**formatting)
        minimal = minimal.format(**formatting)

        for key, value in formatting.items():
            if key[0] == "~":
                formatting[key] = self._color(value)
        pretty = pretty.format(**formatting)

        self.events.on("formatted").on(type).call(server=server,
            context=context, line=line, channel=channel, user=user,
            minimal=minimal, pretty=pretty, **kwargs)

    def _mode_symbols(self, user, channel, server):
        modes = list(channel.get_user_modes(user))
        if modes:
            modes = [mode for mode in modes if mode in server.prefix_modes]
            modes.sort(key=lambda x: list(server.prefix_modes.keys()).index(x))
            return server.prefix_modes[modes[0]]
        return ""

    def _privmsg(self, event, channel, user):
        symbols = ""
        if channel:
            symbols = self._mode_symbols(user, channel, event["server"])

        if event["action"]:
            format = "* {SYM}{~NICK} {MSG}"
        else:
            format = "<{SYM}{~NICK}> {MSG}"

        return {"MSG": event["message"], "SYM": symbols}, format

    @utils.hook("send.message.channel")
    @utils.hook("received.message.channel")
    def channel_message(self, event):
        formatting, line = self._privmsg(event, event["channel"], event["user"])

        self._event("message.channel", event["server"], line,
            event["channel"].name, channel=event["channel"], user=event["user"],
            parsed_line=event["line"], formatting=formatting)

    def _on_notice(self, event, user, channel):
        symbols = ""
        if channel:
            symbols = self._mode_symbols(user, channel, event["server"])

        return {"MSG": event["message"], "SYM": symbols}, "-{SYM}{~NICK}- {MSG}"

    def _channel_notice(self, event, user, channel):
        formatting, line = self._on_notice(event, user, channel)

        self._event("notice.channel", event["server"], line,
            event["channel"].name, parsed_line=event["line"], channel=channel,
            user=event["user"], formatting=formatting)

    @utils.hook("received.notice.channel")
    @utils.hook("send.notice.channel")
    def channel_notice(self, event):
        self._channel_notice(event, event["user"], event["channel"])

    @utils.hook("received.notice.private")
    @utils.hook("send.notice.private")
    def private_notice(self, event):
        formatting, line = self._on_notice(event, event["user"], None)
        self._event("notice.private", event["server"], line,
            event["target"].nickname, parsed_line=event["line"],
            user=event["user"], formatting=formatting)

    def _on_join(self, event, user):
        channel_name = event["channel"].name

        account = ""
        if event["account"]:
            account = " [{ACC}]"
        realname = ""
        if event["realname"]:
            realname = " ({REAL})"

        minimal = "{~NICK} joined {CHAN}"
        line = "- {~NICK}%s%s ({UH}) joined {CHAN}" % (account, realname)

        formatting = {"UH": user.userhost(), "CHAN": event["channel"].name,
            "ACC": event["account"], "REAL": event["realname"]}

        self._event("join", event["server"], line, event["channel"].name,
            channel=event["channel"], user=user, minimal=minimal,
            formatting=formatting)
    @utils.hook("received.join")
    def join(self, event):
        self._on_join(event, event["user"])
    @utils.hook("self.join")
    def self_join(self, event):
        self._on_join(event, event["server"].get_user(event["server"].nickname))

    @utils.hook("received.chghost")
    def _on_chghost(self, event):
        username = event["user"].username
        hostname = event["user"].hostname

        minimal = "{~NICK} changed host to {USER}@{HOST}"
        line = "- %s" % minimal

        self._event("chghost", event["server"], line, None, user=event["user"],
            minimal=minimal, formatting={"USER": username, "HOST": hostname})

    @utils.hook("received.account.login")
    def account_login(self, event):
        self._account(event, "in")
    @utils.hook("received.account.logout")
    def account_logout(self, event):
        self._account(event, "out")
    def _account(self, event, action):
        minimal = "{~NICK} logged %s as {ACC}" % action
        line = "- %s" % minimal

        self._event("account", event["server"], line, None, user=event["user"],
            minimal=minimal, formatting={"ACC": event["account"]})

    def _on_part(self, event, user):
        channel_name = event["channel"].name
        reason = event["reason"]
        reason = "" if not reason else " (%s)" % reason

        minimal = "{~NICK} left {CHAN}{REAS}"
        line = "- %s" % minimal

        self._event("part", event["server"], line, event["channel"].name,
            channel=event["channel"], user=user, minimal=minimal,
            formatting={"CHAN": channel_name, "REAS": reason})
    @utils.hook("received.part")
    def part(self, event):
        self._on_part(event, event["user"])
    @utils.hook("self.part")
    def self_part(self, event):
        self._on_part(event, event["server"].get_user(event["server"].nickname))

    def _on_nick(self, event, user):
        formatting = {"~ONICK": event["old_nickname"],
            "~NNICK": event["new_nickname"]}

        minimal = "{~ONICK} changed nickname to {~NNICK}"
        line = "- %s" % minimal

        self._event("nick", event["server"], line, None, user=user,
            minimal=minimal, formatting=formatting)
    @utils.hook("received.nick")
    def nick(self, event):
        self._on_nick(event, event["user"])
    @utils.hook("self.nick")
    def self_nick(self, event):
        self._on_nick(event, event["server"].get_user(event["server"].nickname))

    @utils.hook("received.invite")
    def invite(self, event):
        formatting = {"CHAN": event["target_channel"],
            "~TNICK": event["target_user"].nickname}

        minimal = "{~NICK} invited {~TNICK} to {CHAN}"
        line = "- %s" % minimal

        self._event("invite", event["server"], line, event["target_channel"],
            user=event["user"], minimal=minimal, formatting=formatting)

    @utils.hook("received.mode.channel")
    def mode(self, event):
        modes = "".join(event["modes_str"])
        args = " ".join(event["args_str"])
        if args:
            args = " %s" % args

        minimal = "{~NICK} set mode {MODE}{ARGS}"
        line = "- %s" % minimal

        self._event("mode.channel", event["server"], line,
            event["channel"].name, channel=event["channel"], user=event["user"],
            minimal=minimal, formatting={"MODE": modes, "ARGS": args})

    def _on_topic(self, event, nickname, action, topic):
        formatting = {"ACT": action, "TOP": topic, "~TNICK": nickname}
        minimal = "topic {ACT} by {~TNICK}: {TOP}"
        line = "- %s" % minimal

        self._event("topic", event["server"], line, event["channel"].name,
            channel=event["channel"], user=event.get("user", None),
            minimal=minimal, formatting=formatting)
    @utils.hook("received.topic")
    def on_topic(self, event):
        self._on_topic(event, event["user"].nickname, "changed",
            event["topic"])
    @utils.hook("received.333")
    def on_333(self, event):
        self._on_topic(event, event["setter"].nickname, "set",
            event["channel"].topic)

        dt = utils.datetime.format.datetime_human(
            utils.datetime.timestamp(event["set_at"]))

        minimal = "topic set at %s" % dt
        line = "- %s" % minimal

        self._event("topic-timestamp", event["server"], line,
            event["channel"].name, channel=event["channel"], minimal=minimal)

    def _on_kick(self, event, kicked_nickname):
        reason = ""
        if event["reason"]:
            reason = " (%s)" % event["reason"]

        formatting = {"CHAN": event["channel"].name, "REAS": reason,
            "~KNICK": kicked_nickname}

        minimal = "{~NICK} kicked {~KNICK} from {CHAN}{REAS}"
        line = "- %s" % minimal

        self._event("kick", event["server"], line, event["channel"].name,
            channel=event["channel"], user=event["user"], minimal=minimal,
            formatting=formatting)
    @utils.hook("received.kick")
    def kick(self, event):
        self._on_kick(event, event["target_user"].nickname)
    @utils.hook("self.kick")
    def self_kick(self, event):
        self._on_kick(event, event["server"].nickname)

    def _quit(self, event, user, reason):
        reason = "" if not reason else " (%s)" % reason

        minimal = "{~NICK} quit{REAS}"
        line = "- %s" % minimal

        self._event("quit", event["server"], line, None, user=user,
            minimal=minimal, formatting={"REAS": reason})
    @utils.hook("received.quit")
    def on_quit(self, event):
        self._quit(event, event["user"], event["reason"])
    @utils.hook("send.quit")
    def send_quit(self, event):
        self._quit(event, event["server"].get_user(event["server"].nickname),
            event["reason"])

    @utils.hook("received.rename")
    def rename(self, event):
        line = "{OLD} was renamed to {NEW}"
        self._event("rename", event["server"], line, event["old_name"],
            channel=event["channel"],
            formatting={"OLD": event["old_name"], "NEW": event["new_name"]})

    @utils.hook("received.376")
    def motd_end(self, event):
        for motd_line in event["server"].motd_lines:
            line = "[MOTD] {LINE}"
            self._event("motd", event["server"], line, None,
                formatting={"LINE": motd_line})
