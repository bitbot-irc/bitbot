import datetime
from src import EventManager, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _color(self, nickname):
        return utils.irc.hash_colorize(nickname)

    def _event(self, type, server, line, context, minimal=None, pretty=None,
            channel=None, user=None, **kwargs):
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

    def _privmsg(self, event, channel, user, nickname):
        symbols = ""
        if channel:
            symbols = self._mode_symbols(user, channel, event["server"])

        if event["action"]:
            format = "* %s%s %s"
        else:
            format = "<%s%s> %s"

        minimal = format % ("", nickname, event["message"])
        normal = format % (symbols, nickname, event["message"])
        pretty = format % (symbols, self._color(nickname),
            event["message"])

        return minimal, normal, pretty

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

        minimal, normal, pretty = self._privmsg(event, event["channel"], user,
            nickname)

        self._event("message.channel", event["server"], normal,
            event["channel"].name, channel=event["channel"], user=user,
            parsed_line=event["line"], minimal=minimal, pretty=pretty)

    def _on_notice(self, event, nickname):
        format = "-%s- %s"
        minimal = format % (nickname, event["message"])
        normal = minimal
        pretty = format % (self._color(nickname), event["message"])

        return minimal, normal, pretty
    def _channel_notice(self, event, nickname, channel):
        minimal, normal, pretty = self._on_notice(event, nickname)
        self._event("notice.channel", event["server"], normal,
            event["channel"].name, parsed_line=event["line"], channel=channel,
            user=event["user"], minimal=minimal, pretty=pretty)

    def _private_notice(self, event, nickname, target):
        minimal, normal, pretty = self._on_notice(event, nickname)
        self._event("notice.private", event["server"], normal, None,
            parsed_line=event["line"], user=event["user"], minimal=minimal,
            pretty=pretty)

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
        channel_name = event["channel"].name

        minimal = "%s joined %s" % (user.nickname, channel_name)

        normal_format = "- %s (%s) joined %s"
        normal = normal_format % (user.nickname, user.userhost(), channel_name)
        pretty = normal_format % (self._color(user.nickname), user.userhost(),
            channel_name)

        self._event("join", event["server"], normal, event["channel"].name,
            channel=event["channel"], user=user, minimal=minimal,
            pretty=pretty)
    @utils.hook("received.join")
    def join(self, event):
        self._on_join(event, event["user"])
    @utils.hook("self.join")
    def self_join(self, event):
        self._on_join(event, event["server"].get_user(event["server"].nickname))

    @utils.hook("received.chghost")
    def _on_chghost(self, event):
        format = "%s changed host to %s@%s" % ("%s", event["username"],
            event["hostname"])
        minimal = format % nickname

        normal_format = "- %s" % format
        normal = normal_format % nickname
        pretty = normal_format % self._color(nickname)

        self._event("chghost", event["server"], normal, None,
            user=event["user"], minimal=minimal, pretty=pretty)

    def _on_part(self, event, user):
        reason = event["reason"]
        reason = "" if not reason else " (%s)" % reason

        format = "%s left %s%s" % ("%s", event["channel"].name, reason)
        minimal = format % nickname

        normal_format = "- %s" % format
        normal = normal_format % nickname
        pretty = normal_format % self._color(nickname)

        self._event("part", event["server"], normal, event["channel"].name,
            channel=event["channel"], user=user, minimal=minimal, pretty=pretty)
    @utils.hook("received.part")
    def part(self, event):
        self._on_part(event, event["user"])
    @utils.hook("self.part")
    def self_part(self, event):
        self._on_part(event, event["server"].get_user(event["server"].nickname))

    def _on_nick(self, event, user):
        old_nickname = event["old_nickname"]
        new_nickname = event["new_nickname"]

        format = "%s changed nickname to %s"
        minimal = format % (old_nickname, new_nickname)

        normal_format = "- %s" % format
        normal = normal_format % (old_nickname, new_nickname)
        pretty = normal_format % (
            self._color(old_nickname), self._color(new_nickname))

        self._event("nick", event["server"], normal, None, user=user,
            minimal=minimal, pretty=pretty)
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
        format = "%s invited %s to %s" % ("%s", "%s", event["target_channel"])
        minimal = format % (event["user"].nickname,
            event["target_user"].nickname)
        normal = "- %s" % minimal
        pretty = format % (self._color(event["user"].nickname),
            self._color(event["target_user"].nickname))

        self._event("invite", event["server"], normal, event["target_channel"],
            minimal=minimal, pretty=pretty)

    @utils.hook("received.mode.channel")
    def mode(self, event):
        args = " ".join(event["args_str"])
        if args:
            args = " %s" % args

        format = "%s set mode %s%s" % ("%s", "".join(event["mode_str"]),
            args)
        minimal = format % event["user"].nickname

        normal_format = "- %s" % format
        normal = normal_format % event["user"].nickname
        pretty = normal_format % self._color(event["user"].nickname)

        self._event("mode.channel", event["server"], normal,
            event["channel"].name, channel=event["channel"], user=event["user"],
            minimal=minimal, pretty=pretty)

    def _on_topic(self, event, nickname, action, topic):
        format = "topic %s by %s: %s" % (action, "%s", topic)
        minimal = format % nickname

        normal_format = "- %s" % format
        normal = normal_format % nickname
        pretty = normal_format % self._color(nickname)

        self._event("topic", event["server"], normal, event["channel"].name,
            channel=event["channel"], user=event.get("user", None),
            minimal=minimal, pretty=pretty)
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

    def _on_kick(self, event, kicked_nickname):
        sender_nickname = event["user"].nickname

        reason = ""
        if event["reason"]:
            reason = " (%s)" % event["reason"]

        format = "%s kicked %s from %s%s" % ("%s", "%s", event["channel"].name,
            reason)
        minimal = format % (sender_nickname, kicked_nickname)

        normal_format = "- %s" % format
        normal = normal_format % (sender_nickname, kicked_nickname)
        pretty = normal_format % (self._color(sender_nickname),
            self._color(kicked_nickname))

        self._event("kick", event["server"], normal, event["channel"].name,
            channel=event["channel"], user=event.get("user", None),
            minimal=minimal, pretty=pretty)
    @utils.hook("received.kick")
    def kick(self, event):
        self._on_kick(event, event["target_user"].nickname)
    @utils.hook("self.kick")
    def self_kick(self, event):
        self._on_kick(event, event["server"].nickname)

    def _quit(self, event, user, reason):
        reason = "" if not reason else " (%s)" % reason

        format = "%s quit%s" % ("%s", reason)
        minimal = format % user.nickname

        normal_format = "- %s" % format
        normal = normal_format % user.nickname
        pretty = normal_format % self._color(user.nickname)

        self._event("quit", event["server"], normal, None, user=user,
            minimal=minimal, pretty=pretty)
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
