import datetime
from src import EventManager, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _event(self, type, server, line, context):
        self.events.on("formatted").on(type).call(server=server, line=line,
            context=context)

    def _mode_symbols(self, user, channel, server):
        modes = channel.get_user_status(user)
        symbols = []
        modes = list(channel.get_user_status(user))
        modes.sort(key=lambda x: list(server.prefix_modes.keys()).index(x))
        for mode in modes:
            symbols.append(server.prefix_modes[mode])
        return "".join(symbols)

    def _privmsg(self, event, channel, user, nickname):
        symbols = ""
        if channel:
            symbols = self._mode_symbols(user, channel, event["server"])

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
            event["channel"].name)

    def _on_notice(self, event, sender, target):
        line = "(notice->%s) <%s> %s" % (
            target, sender, event["message"])
        self._event("notice.channel", event["server"], line, None)
    @utils.hook("received.notice.channel", priority=EventManager.PRIORITY_HIGH)
    def channel_notice(self, event):
        self._on_notice(event, event["user"].nickname, event["channel"].name)
    @utils.hook("send.notice.channel")
    def self_notice_channel(self, event):
        self._on_notice(event, event["server"].nickname, event["channel"].name)
    @utils.hook("received.notice.private", priority=EventManager.PRIORITY_HIGH)
    def private_notice(self, event):
        self._on_notice(event, event["user"].nickname, event["server"].nickname)
    @utils.hook("send.notice.private")
    def self_private_notice(self, event):
        self._on_notice(event, event["server"].nickname, event["user"].nickname)

    def _on_join(self, event, nickname):
        line = "%s joined %s" % (nickname, event["channel"].name)
        self._event("join", event["server"], line, event["channel"].name)
    @utils.hook("received.join")
    def join(self, event):
        self._on_join(event, event["user"].nickname)
    @utils.hook("self.join")
    def self_join(self, event):
        self._on_join(event, event["server"].nickname)

    def _on_part(self, event, nickname):
        reason = ""
        if event["reason"]:
            reason = " (%s)" % event["reason"]
        line = "%s left %s%s" % (nickname, event["channel"].name, reason)
        self._event("part", event["server"], line, event["channel"].name)
    @utils.hook("received.part")
    def part(self, event):
        self._on_part(event, event["user"].nickname)
    @utils.hook("self.part")
    def self_part(self, event):
        self._on_part(event, event["server"].nickname)

    @utils.hook("received.nick")
    @utils.hook("self.nick")
    def on_nick(self, event):
        line = "%s changed nickname to %s" % (
            event["old_nickname"], event["new_nickname"])
        self._event("nick", event["server"], line, None)

    @utils.hook("received.server-notice", priority=EventManager.PRIORITY_HIGH)
    def server_notice(self, event):
        line = "(server notice) %s" % event["message"]
        self._event("server-notice", event["server"], line, None)

    @utils.hook("received.invite")
    def invite(self, event):
        line = "%s invited %s to %s" % (
            event["user"].nickname, event["target_user"].nickname,
            event["target_channel"])
        self._event("invite", event["server"], line, event["target_channel"])

    @utils.hook("received.mode.channel")
    def mode(self, event):
        args = " ".join(event["mode_args"])
        if args:
            args = " %s" % args

        line = "%s set mode %s%s" % (
            event["user"].nickname, "".join(event["modes"]), args)
        self._event("mode.channel", event["server"], line,
            event["channel"].name)

    def _on_topic(self, event, setter, action, topic):
        line = "topic %s by %s: %s" % (action, setter, topic)
        self._event("topic", event["server"], line, event["channel"].name)
    @utils.hook("received.topic")
    def on_topic(self, event):
        self._on_topic(event, event["user"].nickname, "changed",
            event["topic"])
    @utils.hook("received.333")
    def on_333(self, event):
        self._on_topic(event, event["setter"], "set",
            event["channel"].topic)

        unix_dt = datetime.datetime.utcfromtimestamp(event["set_at"])
        dt = datetime.datetime.strftime(unix_dt, utils.ISO8601_PARSE)
        line = "topic set at %s" % dt
        self._event("topic-timestamp", event["server"], line,
            event["channel"].name)

    def _on_kick(self, event, nickname):
        reason = ""
        if event["reason"]:
            reason = "(%s)" % event["reason"]
        line = "%s kicked %s from %s%s" % (
            event["user"].nickname, nickname, event["channel"].name, reason)
        self._event("kick", event["server"], line, event["channel"].name)
    @utils.hook("received.kick")
    def kick(self, event):
        self._on_kick(event, event["target_user"].nickname)
    @utils.hook("self.kick")
    def self_kick(self, event):
        self._on_kick(event, event["server"].nickname)

    def _quit(self, event, nickname, reason):
        reason = ""
        if reason:
            reason = " (%s)" % reason
        line = "%s quit%s" % (nickname, reason)
        self._event("quit", event["server"], line, None)
    @utils.hook("received.quit")
    def on_quit(self, event):
        self._quit(event, event["user"].nickname, event["reason"])
    @utils.hook("send.quit")
    def send_quit(self, event):
        self._quit(event, event["server"].nickname, event["reason"])

    @utils.hook("received.rename")
    def rename(self, event):
        line = "%s was renamed to %s" % (event["old_name"], event["new_name"])
        self._event("rename", event["server"], line, event["old_name"])

    @utils.hook("received.376")
    def motd_end(self, event):
        for line in event["server"].motd_lines:
            line = "[MOTD] %s" % line
            self._event("motd", event["server"], line, None)
