import datetime
from src import EventManager, ModuleManager, utils

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

class Module(ModuleManager.BaseModule):
    def print_line(self, event, line, channel=None):
        timestamp = datetime.datetime.now().isoformat()
        target = str(event["server"])
        if not channel == None:
            target += channel
        formatted_line = utils.irc.parse_format(line)
        self.bot.log.info("%s | %s", [target, formatted_line])

    def _mode_symbols(self, user, channel, server):
        modes = channel.get_user_status(user)
        symbols = []
        modes = list(channel.get_user_status(user))
        modes.sort(key=lambda x: list(server.prefix_modes.keys()).index(x))
        for mode in modes:
            symbols.append(server.prefix_modes[mode])
        return "".join(symbols)

    def _on_message(self, event, user):
        symbols = self._mode_symbols(user, event["channel"],
            event["server"])
        if event["action"]:
            self.print_line(event, "* %s%s %s" % (symbols, user.nickname,
                event["message"]), channel=event["channel"].name)
        else:
            self.print_line(event, "<%s%s> %s" % (symbols, user.nickname,
                event["message"]), channel=event["channel"].name)
    @utils.hook("received.message.channel",
        priority=EventManager.PRIORITY_HIGH)
    def channel_message(self, event):
        self._on_message(event, event["user"])
    @utils.hook("send.message.channel")
    def self_channel_message(self, event):
        self._on_message(event, event["server"].get_user(
            event["server"].nickname))

    def _on_notice(self, event, sender, target):
        self.print_line(event, "(notice->%s) <%s> %s" % (
            target, sender, event["message"]))
    @utils.hook("received.notice.channel",
        priority=EventManager.PRIORITY_HIGH)
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

    @utils.hook("received.server-notice", priority=EventManager.PRIORITY_HIGH)
    def server_notice(self, event):
        self.print_line(event, "(server notice) %s" % event["message"])

    def _on_join(self, event, nickname):
        self.print_line(event, "%s joined %s" % (nickname,
            event["channel"].name))
    @utils.hook("received.join")
    def join(self, event):
        self._on_join(event, event["user"].nickname)
    @utils.hook("self.join")
    def self_join(self, event):
        self._on_join(event, event["server"].nickname)

    def _on_part(self, event, nickname):
        self.print_line(event, "%s left %s%s" % (
            nickname,
            event["channel"].name,
            "" if not event["reason"] else " (%s)" % event["reason"]))
    @utils.hook("received.part")
    def part(self, event):
        self._on_part(event, event["user"].nickname)
    @utils.hook("self.part")
    def self_part(self, event):
        self._on_part(event, event["server"].nickname)

    @utils.hook("received.nick")
    @utils.hook("self.nick")
    def on_nick(self, event):
        self.print_line(event, "%s changed nickname to %s" % (
            event["old_nickname"], event["new_nickname"]))

    @utils.hook("received.quit")
    def on_quit(self, event):
        self.print_line(event, "%s quit%s" % (event["user"].nickname,
            "" if not event["reason"] else " (%s)" % event["reason"]))

    def _on_kick(self, event, nickname):
        self.print_line(event, "%s kicked %s from %s%s" % (
            event["user"].nickname, nickname, event["channel"].name,
            "" if not event["reason"] else " (%s)" % event["reason"]))
    @utils.hook("received.kick")
    def kick(self, event):
        self._on_kick(event, event["target_user"].nickname)
    @utils.hook("self.kick")
    def self_kick(self, event):
        self._on_kick(event, event["server"].nickname)

    def _on_topic(self, event, setter, action, topic, channel):
        self.print_line(event, "topic %s by %s: %s" % (action, setter,
            topic), channel=channel.name)
    @utils.hook("received.topic")
    def on_topic(self, event):
        self._on_topic(event, event["user"].nickname, "changed",
            event["topic"], event["channel"])
    @utils.hook("received.numeric.333")
    def on_333(self, event):
        self._on_topic(event, event["setter"], "set",
            event["channel"].topic, event["channel"])

        unix_dt = datetime.datetime.utcfromtimestamp(event["set_at"])
        dt = datetime.datetime.strftime(unix_dt, DATETIME_FORMAT)
        self.print_line(event, "topic set at %s" % dt,
            channel=event["channel"].name)

    @utils.hook("received.mode.channel")
    def mode(self, event):
        args = " ".join(event["mode_args"])
        if args:
            args = " %s" % args
        self.print_line(event, "%s set mode %s%s" % (
            event["user"].nickname, "".join(event["modes"]),
            args), channel=event["channel"].name)

    @utils.hook("received.rename")
    def rename(self, event):
        self.print_line(event, "%s was renamed to %s" % (
            event["old_name"], event["new_name"]))

    @utils.hook("received.numeric.376")
    def motd_end(self, event):
        for line in event["server"].motd_lines:
            self.print_line(event, "[MOTD] %s" % line)

    @utils.hook("received.invite")
    def invite(self, event):
        self.print_line(event, "%s invited %s to %s" % (
            event["user"].nickname, event["target_user"].nickname,
            event["target_channel"]))
