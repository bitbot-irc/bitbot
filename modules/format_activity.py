import datetime
from src import EventManager, ModuleManager, utils

@utils.export("botset", utils.BoolSetting("colorize-nicknames",
    "Whether or not to format nicknames with calculated colors"))
class Module(ModuleManager.BaseModule):
    def _colorize(self, nickname):
        if self.bot.get_setting("colorize-nicknames", False):
            return utils.irc.hash_colorize(nickname)
        return nickname

    def _event(self, type, server, line, context, minimal=None,
            channel=None, user=None, **kwargs):
        self.events.on("formatted").on(type).call(server=server,
            context=context, line=line, channel=channel, user=user,
            minimal=minimal, **kwargs)

    def _mode_symbols(self, user, channel, server):
        modes = list(channel.get_user_modes(user))
        if modes:
            modes = [mode for mode in modes if mode in server.prefix_modes]
            modes.sort(key=lambda x: list(server.prefix_modes.keys()).index(x))
            return server.prefix_modes[modes[0]]
        return ""

    def _privmsg(self, event, channel, user, nickname):
        symbols = ""
        if channel:
            symbols = self._mode_symbols(user, channel, event["server"])

        nickname = self._colorize(nickname)

        if event["action"]:
            return "* %s%s %s" % (symbols, nickname, event["message"])
        else:
            return "<%s%s> %s" % (symbols, nickname, event["message"])

    @utils.hook("send.message.channel")
    @utils.hook("received.message.channel")
    def channel_message(self, event):
        nickname = None
        user = None
        if "user" in event and event["user"]:
            user = event["user"]
            nickname = event["user"].nickname
        else:
            nickname = event["server"].nickname
            user = event["server"].get_user(nickname)

        line = self._privmsg(event, event["channel"], user, nickname)
        self._event("message.channel", event["server"], line,
            event["channel"].name, channel=event["channel"], user=user,
            parsed_line=event["line"])

    def _on_notice(self, event, nickname):
        nickname = self._colorize(nickname)
        return "(notice) <%s> %s" % (nickname, event["message"])
    def _channel_notice(self, event, nickname, channel):
        line = self._on_notice(event, nickname)
        self._event("notice.channel", event["server"], line,
            event["channel"].name, parsed_line=event["line"], channel=channel,
            user=event["user"])

    def _private_notice(self, event, nickname, target):
        line = self._on_notice(event, nickname)
        self._event("notice.private", event["server"], line, None,
            parsed_line=event["line"], user=event["user"])

    @utils.hook("received.notice.channel")
    def channel_notice(self, event):
        self._channel_notice(event, event["user"].nickname, event["channel"])
    @utils.hook("send.notice.channel")
    def self_notice_channel(self, event):
        self._channel_notice(event, event["server"].nickname, event["channel"])
    @utils.hook("received.notice.private")
    def private_notice(self, event):
        self._private_notice(event, event["user"].nickname,
            event["server"].nickname)
    @utils.hook("send.notice.private")
    def self_private_notice(self, event):
        self._private_notice(event, event["server"].nickname,
            event["user"].nickname)

    def _on_join(self, event, user):
        nickname = self._colorize(user.nickname)
        hostmask = "%s!%s" % (nickname, user.userhost())
        line = "- %s joined %s" % (hostmask, event["channel"].name)
        minimal_line = "%s joined %s" % (nickname, event["channel"].name)

        self._event("join", event["server"], line, event["channel"].name,
            channel=event["channel"], user=user, minimal=minimal_line)
    @utils.hook("received.join")
    def join(self, event):
        self._on_join(event, event["user"])
    @utils.hook("self.join")
    def self_join(self, event):
        self._on_join(event, event["server"].get_user(event["server"].nickname))

    @utils.hook("received.chghost")
    def _on_chghost(self, event):
        nickname = self._colorize(event["user"].nickname)
        line_minimal = "%s changed host to %s@%s" % (nickname,
            event["username"], event["hostname"])
        line = "- %s" % line_minimal
        self._event("chghost", event["server"], line, None, user=event["user"],
            minimal=line_minimal)

    def _on_part(self, event, user):
        nickname = self._colorize(user.nickname)
        reason = event["reason"]
        reason = "" if not reason else " (%s)" % reason
        line_minimal = "%s left %s%s" % (nickname, event["channel"].name,
            reason)
        line = "- %s" % line_minimal

        self._event("part", event["server"], line, event["channel"].name,
            channel=event["channel"], user=user, minimal=line_minimal)
    @utils.hook("received.part")
    def part(self, event):
        self._on_part(event, event["user"])
    @utils.hook("self.part")
    def self_part(self, event):
        self._on_part(event, event["server"].get_user(event["server"].nickname))

    def _on_nick(self, event, user):
        old_nickname = self._colorize(event["old_nickname"])
        new_nickname = self._colorize(event["new_nickname"])
        line_minimal = "%s changed nickname to %s" % (old_nickname,
            new_nickname)
        line = "- %s" % line_minimal

        self._event("nick", event["server"], line, None, user=user,
            minimal=line_minimal)
    @utils.hook("received.nick")
    def nick(self, event):
        self._on_nick(event, event["user"])
    @utils.hook("self.nick")
    def self_nick(self, event):
        self._on_nick(event, event["server"].get_user(event["server"].nickname))

    @utils.hook("received.server-notice")
    def server_notice(self, event):
        line = "(server notice) %s" % event["message"]
        self._event("server-notice", event["server"], line, None)

    @utils.hook("received.invite")
    def invite(self, event):
        sender_nickname = self._colorize(event["user"].nickname)
        target_nickname = self._colorize(event["target_user"].nickname)
        line = "%s invited %s to %s" % (sender_nickname, target_nickname,
            event["target_channel"])
        self._event("invite", event["server"], line, event["target_channel"])

    @utils.hook("received.mode.channel")
    def mode(self, event):
        args = " ".join(event["args_str"])
        if args:
            args = " %s" % args

        nickname = self._colorize(event["user"].nickname)
        line_minimal = "%s set mode %s%s" % (nickname,
            "".join(event["modes_str"]), args)
        line = "- %s" % line_minimal

        self._event("mode.channel", event["server"], line,
            event["channel"].name, channel=event["channel"], user=event["user"],
            minimal=line_minimal)

    def _on_topic(self, event, nickname, action, topic):
        nickname = self._colorize(nickname)
        line = "topic %s by %s: %s" % (action, nickname, topic)
        self._event("topic", event["server"], line, event["channel"].name,
            channel=event["channel"], user=event.get("user", None))
    @utils.hook("received.topic")
    def on_topic(self, event):
        self._on_topic(event, event["user"].nickname, "changed",
            event["topic"])
    @utils.hook("received.333")
    def on_333(self, event):
        self._on_topic(event, event["setter"].nickname, "set",
            event["channel"].topic)

        unix_dt = datetime.datetime.utcfromtimestamp(event["set_at"])
        dt = datetime.datetime.strftime(unix_dt, utils.ISO8601_PARSE)
        line = "topic set at %s" % dt
        self._event("topic-timestamp", event["server"], line,
            event["channel"].name, channel=event["channel"])

    def _on_kick(self, event, nickname):
        sender_nickname = self._colorize(event["user"].nickname)
        kicked_nickname = self._colorize(nickname)

        reason = ""
        if event["reason"]:
            reason = " (%s)" % event["reason"]
        line_minimal = "%s kicked %s from %s%s" % (
            sender_nickname, kicked_nickname, event["channel"].name, reason)
        line = "- %s" % line_minimal

        self._event("kick", event["server"], line, event["channel"].name,
            channel=event["channel"], user=event.get("user", None),
            minimal=line_minimal)
    @utils.hook("received.kick")
    def kick(self, event):
        self._on_kick(event, event["target_user"].nickname)
    @utils.hook("self.kick")
    def self_kick(self, event):
        self._on_kick(event, event["server"].nickname)

    def _quit(self, event, user, reason):
        nickname = self._colorize(user.nickname)
        reason = "" if not reason else " (%s)" % reason
        line_minimal = "%s quit%s" % (nickname, reason)
        line = "- %s" % line_minimal

        self._event("quit", event["server"], line, None, user=user,
            minimal=line_minimal)
    @utils.hook("received.quit")
    def on_quit(self, event):
        self._quit(event, event["user"], event["reason"])
    @utils.hook("send.quit")
    def send_quit(self, event):
        self._quit(event, event["server"].get_user(event["server"].nickname),
            event["reason"])

    @utils.hook("received.rename")
    def rename(self, event):
        line = "%s was renamed to %s" % (event["old_name"], event["new_name"])
        self._event("rename", event["server"], line, event["old_name"],
            channel=event["channel"])

    @utils.hook("received.376")
    def motd_end(self, event):
        for line in event["server"].motd_lines:
            line = "[MOTD] %s" % line
            self._event("motd", event["server"], line, None)
