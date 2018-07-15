import datetime
import EventManager

class Module(object):
    def __init__(self, bot):
        self.bot = bot

        bot.events.on("received").on("message").on("channel").hook(
            self.channel_message,
            priority=EventManager.EventCallback.PRIORITY_HIGH)
        bot.events.on("self").on("message").on("channel").hook(
            self.self_channel_message)

        bot.events.on("received").on("join").hook(self.join)
        bot.events.on("self").on("join").hook(self.self_join)

        bot.events.on("received").on("part").hook(self.part)
        bot.events.on("self").on("part").hook(self.self_part)

        bot.events.on("received").on("nick").hook(self.on_nick)
        bot.events.on("self").on("nick").hook(self.on_nick)

        bot.events.on("received").on("quit").hook(self.on_quit)

        bot.events.on("received").on("kick").hook(self.kick)
        bot.events.on("self").on("kick").hook(self.self_kick)

    def print_line(self, event, line):
        timestamp = datetime.datetime.now().isoformat()
        target = str(event["server"])
        if "channel" in event:
            target += event["channel"].name
        print("[%s] %s | %s" % (timestamp, target, line))

    def _on_message(self, event, nickname):
        if not self.bot.args.verbose:
            if event["action"]:
                self.print_line(event, "* %s %s" % (nickname, event["message"]))
            else:
                self.print_line(event, "<%s> %s" % (nickname, event["message"]))
    def channel_message(self, event):
        self._on_message(event, event["user"].nickname)
    def self_channel_message(self, event):
        self._on_message(event, event["server"].nickname)

    def _on_join(self, event, nickname):
        if not self.bot.args.verbose:
            self.print_line(event, "%s joined %s" % (nickname,
                event["channel"].name))
    def join(self, event):
        self._on_join(event, event["user"].nickname)
    def self_join(self, event):
        self._on_join(event, event["server"].nickname)

    def _on_part(self, event, nickname):
        if not self.bot.args.verbose:
            self.print_line(event, "%s left %s%s" % (nickname,
                event["channel"].name, "" if not event[
                "reason"] else " (%s)" % event["reason"]))
    def part(self, event):
        self._on_part(event, event["user"].nickname)
    def self_part(self, event):
        self._on_part(event, event["server"].nickname)

    def on_nick(self, event):
        if not self.bot.args.verbose:
            self.print_line(event, "%s changed nickname to %s" % (
                event["old_nickname"], event["new_nickname"]))

    def on_quit(self, event):
        if not self.bot.args.verbose:
            self.print_line(event, "%s quit" % event["user"].nickname)

    def _on_kick(self, event, nickname):
        if not self.bot.args.verbose:
            self.print_line(event, "%s kicked %s from %s%s" % (
                event["user"].nickname, nickname, event["channel"].name,
                "" if not event["reason"] else " (%s)" % event["reason"]))
    def kick(self, event):
        self._on_kick(event, event["target_user"].nickname)
    def self_kick(self, event):
        self._on_kick(event, event["server"].nickname)
