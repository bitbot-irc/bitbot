import datetime
from bitbot import EventManager, ModuleManager, utils

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

    def _privmsg(self, event, channel, user):
        symbols = ""
        if channel:
            symbols = self._mode_symbols(user, channel, event["server"])

        if event["action"]:
            format = "* %s%s %s"
        else:
            format = "<%s%s> %s"

        minimal = format % ("", user.nickname, event["message"])
        normal = format % (symbols, user.nickname, event["message"])
        pretty = format % (symbols, self._color(user.nickname),
            event["message"])

        return minimal, normal, pretty

    @utils.hook("send.message.channel")
    @utils.hook("received.message.channel")
    def channel_message(self, event):
        minimal, normal, pretty = self._privmsg(event, event["channel"],
            event["user"])

        self._event("message.channel", event["server"], normal,
            event["channel"].name, channel=event["channel"], user=event["user"],
            parsed_line=event["line"], minimal=minimal, pretty=pretty)

    def _on_notice(self, event, user, channel):
        symbols = ""
        if channel:
            symbols = self._mode_symbols(user, channel, event["server"])

        format = "-%s%s- %s"
        minimal = format % ("", user.nickname, event["message"])
        normal = format % (symbols, user.nickname, event["message"])
        pretty = format % (symbols, self._color(user.nickname),
            event["message"])

        return minimal, normal, pretty
    def _channel_notice(self, event, user, channel):
        minimal, normal, pretty = self._on_notice(event, user, channel)
        self._event("notice.channel", event["server"], normal,
            event["channel"].name, parsed_line=event["line"], channel=channel,
            user=event["user"], minimal=minimal, pretty=pretty)

    @utils.hook("received.notice.channel")
    @utils.hook("send.notice.channel")
    def channel_notice(self, event):
        self._channel_notice(event, event["user"], event["channel"])

    @utils.hook("received.notice.private")
    @utils.hook("send.notice.private")
    def private_notice(self, event):
        minimal, normal, pretty = self._on_notice(event, event["user"], None)
        self._event("notice.private", event["server"], normal,
            event["target"].nickname, parsed_line=event["line"],
            user=event["user"], minimal=minimal, pretty=pretty)

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
        username = event["username"]
        hostname = event["hostname"]

        format = "%s changed host to %s@%s"
        minimal = format % (event["user"].nickname, username, hostname)

        normal_format = "- %s" % format
        normal = normal_format % (event["user"].nickname, username, hostname)
        pretty = normal_format % (self._color(event["user"].nickname), username,
            hostname)

        self._event("chghost", event["server"], normal, None,
            user=event["user"], minimal=minimal, pretty=pretty)

    def _on_part(self, event, user):
        channel_name = event["channel"].name
        reason = event["reason"]
        reason = "" if not reason else " (%s)" % reason

        format = "%s left %s%s"
        minimal = format % (user.nickname, channel_name, reason)

        normal_format = "- %s" % format
        normal = normal_format % (user.nickname, channel_name, reason)
        pretty = normal_format % (self._color(user.nickname), channel_name,
            reason)

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
        format = "%s invited %s to %s"

        sender = event["user"].nickname
        target = event["target_user"].nickname
        channel_name = event["target_channel"]

        minimal = format % (sender, target, channel_name)
        normal = "- %s" % minimal
        pretty = format % (self._color(sender), target, channel_name)

        self._event("invite", event["server"], normal, event["target_channel"],
            minimal=minimal, pretty=pretty)

    @utils.hook("received.mode.channel")
    def mode(self, event):
        modes = "".join(event["modes_str"])
        args = " ".join(event["args_str"])
        if args:
            args = " %s" % args

        format = "%s set mode %s%s"
        minimal = format % (event["user"].nickname, modes, args)

        normal_format = "- %s" % format
        normal = normal_format % (event["user"].nickname, modes, args)
        pretty = normal_format % (self._color(event["user"].nickname), modes,
            args)

        self._event("mode.channel", event["server"], normal,
            event["channel"].name, channel=event["channel"], user=event["user"],
            minimal=minimal, pretty=pretty)

    def _on_topic(self, event, nickname, action, topic):
        format = "topic %s by %s: %s"
        minimal = format % (action, nickname, topic)

        normal_format = "- %s" % format
        normal = normal_format % (action, nickname, topic)
        pretty = normal_format % (action, self._color(nickname), topic)

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

        dt = utils.datetime.iso8601_format(
            utils.datetime.datetime_timestamp(event["set_at"]))

        minimal = "topic set at %s" % dt
        normal = "- %s" % minimal

        self._event("topic-timestamp", event["server"], normal,
            event["channel"].name, channel=event["channel"], minimal=minimal)

    def _on_kick(self, event, kicked_nickname):
        sender_nickname = event["user"].nickname
        channel_name = event["channel"].name

        reason = ""
        if event["reason"]:
            reason = " (%s)" % event["reason"]

        format = "%s kicked %s from %s%s"
        minimal = format % (sender_nickname, kicked_nickname, channel_name,
            reason)

        normal_format = "- %s" % format
        normal = normal_format % (sender_nickname, kicked_nickname,
            channel_name, reason)
        pretty = normal_format % (self._color(sender_nickname),
            self._color(kicked_nickname), channel_name, reason)

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

        format = "%s quit%s"
        minimal = format % (user.nickname, reason)

        normal_format = "- %s" % format
        normal = normal_format % (user.nickname, reason)
        pretty = normal_format % (self._color(user.nickname), reason)

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
