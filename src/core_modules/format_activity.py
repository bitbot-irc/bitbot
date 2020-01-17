import datetime
from src import EventManager, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _color(self, nickname):
        return utils.irc.hash_colorize(nickname)

    def _event(self, type, server, line, context, minimal=None, channel=None,
            user=None, formatting={}, **kwargs):
        pretty = line
        minimal = minimal or line

        if user:
            formatting["NICK"] = user.nickname
            line = line.format(**formatting)
            minimal = minimal.format(**formatting)

            for key, value in formatting.items():
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
            format = "* %s{NICK} %s"
        else:
            format = "<%s{NICK}> %s"

        return format % (symbols, event["message"])

    @utils.hook("send.message.channel")
    @utils.hook("received.message.channel")
    def channel_message(self, event):
        line = self._privmsg(event, event["channel"], event["user"])

        self._event("message.channel", event["server"], line,
            event["channel"].name, channel=event["channel"], user=event["user"],
            parsed_line=event["line"])

    def _on_notice(self, event, user, channel):
        symbols = ""
        if channel:
            symbols = self._mode_symbols(user, channel, event["server"])

        return "-%s{NICK}- %s" % (symbols, event["message"])

    def _channel_notice(self, event, user, channel):
        line = self._on_notice(event, user, channel)

        self._event("notice.channel", event["server"], line,
            event["channel"].name, parsed_line=event["line"], channel=channel,
            user=event["user"])

    @utils.hook("received.notice.channel")
    @utils.hook("send.notice.channel")
    def channel_notice(self, event):
        self._channel_notice(event, event["user"], event["channel"])

    @utils.hook("received.notice.private")
    @utils.hook("send.notice.private")
    def private_notice(self, event):
        line= self._on_notice(event, event["user"], None)
        self._event("notice.private", event["server"], line,
            event["target"].nickname, parsed_line=event["line"],
            user=event["user"])

    def _on_join(self, event, user):
        channel_name = event["channel"].name

        minimal = "{NICK} joined %s" % channel_name
        line = "- {NICK} (%s) joined %s" % (user.userhost(), channel_name)

        self._event("join", event["server"], line, event["channel"].name,
            channel=event["channel"], user=user, minimal=minimal)
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

        minimal = "{NICK} changed host to %s@%s" % (username, hostname)
        line = "- %s" % minimal

        self._event("chghost", event["server"], line, None, user=event["user"],
            minimal=minimal)

    def _on_part(self, event, user):
        channel_name = event["channel"].name
        reason = event["reason"]
        reason = "" if not reason else " (%s)" % reason

        minimal = "{NICK} left %s%s" % (channel_name, reason)
        line = "- %s" % minimal

        self._event("part", event["server"], line, event["channel"].name,
            channel=event["channel"], user=user, minimal=minimal)
    @utils.hook("received.part")
    def part(self, event):
        self._on_part(event, event["user"])
    @utils.hook("self.part")
    def self_part(self, event):
        self._on_part(event, event["server"].get_user(event["server"].nickname))

    def _on_nick(self, event, user):
        formatting = {"ONICK": event["old_nickname"],
            "NNICK": event["new_nickname"]}

        minimal = "{ONICK} changed nickname to {NNICK}"
        line = "- %s" % minimal

        self._event("nick", event["server"], line, None, user=user,
            minimal=minimal, formatting=formatting)
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
        formatting = {"TNICK": event["target_user"].nickname}

        channel_name = event["target_channel"]
        minimal = "{NICK} invited {TNICK} to %s" % channel_name
        line = "- %s" % minimal

        self._event("invite", event["server"], line, event["target_channel"],
            user=user, minimal=minimal, formatting=formatting)

    @utils.hook("received.mode.channel")
    def mode(self, event):
        modes = "".join(event["modes_str"])
        args = " ".join(event["args_str"])
        if args:
            args = " %s" % args

        minimal = "{NICK} set mode %s%s" % (modes, args)
        line = "- %s" % minimal

        self._event("mode.channel", event["server"], line,
            event["channel"].name, channel=event["channel"], user=event["user"],
            minimal=minimal)

    def _on_topic(self, event, nickname, action, topic):
        formatting = {"TNICK": nickname}
        minimal = "topic %s by {TNICK}: %s" % (action, topic)
        line = "- %s" % minimal

        self._event("topic", event["server"], line, event["channel"].name,
            channel=event["channel"], user=event["user"], minimal=minimal,
            formatting=formatting)
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
        line = "- %s" % minimal

        self._event("topic-timestamp", event["server"], line,
            event["channel"].name, channel=event["channel"], minimal=minimal)

    def _on_kick(self, event, kicked_nickname):
        formatting = {"KNICK": kicked_nickname}
        channel_name = event["channel"].name

        reason = ""
        if event["reason"]:
            reason = " (%s)" % event["reason"]

        minimal = "{NICK} kicked {KNICK} from %s%s" % (channel_name, reason)
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

        minimal = "{NICK} quit%s" % reason
        line = "- %s" % minimal

        self._event("quit", event["server"], line, None, user=user,
            minimal=minimal)
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
