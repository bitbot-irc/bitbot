import datetime
from src import EventManager, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def print_line(self, event, line, channel=None):
        timestamp = datetime.datetime.now().isoformat()
        target = str(event["server"])
        if not channel == None:
            target += channel
        self.bot.log.info("%s | %s", [target, line])

    def _on_message(self, event, nickname):
        if event["action"]:
            self.print_line(event, "* %s %s" % (nickname, event["message"]),
                channel=event["channel"].name)
        else:
            self.print_line(event, "<%s> %s" % (nickname, event["message"]),
                channel=event["channel"].name)
    @utils.hook("received.message.channel",
        priority=EventManager.PRIORITY_HIGH)
    def channel_message(self, event):
        self._on_message(event, event["user"].nickname)
    @utils.hook("self.message.channel")
    def self_channel_message(self, event):
        self._on_message(event, event["server"].nickname)

    def _on_notice(self, event, target):
        self.print_line(event, "(notice->%s) <%s> %s" % (
            target, event["user"].nickname, event["message"]))
    @utils.hook("received.notice.channel",
        priority=EventManager.PRIORITY_HIGH)
    def channel_notice(self, event):
        self._on_notice(event, event["channel"].name)
    @utils.hook("received.notice.private", priority=EventManager.PRIORITY_HIGH)
    def private_notice(self, event):
        self._on_notice(event, event["server"].nickname)
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

    @utils.hook("received.mode.channel")
    def mode(self, event):
        args = " ".join(event["mode_args"])
        if args:
            args = " %s" % args
        self.print_line(event, "%s set mode %s%s" % (
            event["user"].nickname, "".join(event["modes"]),
            args), channel=event["channel"].name)
