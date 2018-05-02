import datetime

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("message").on("channel").hook(
            self.on_message)
        bot.events.on("received").on("join").hook(self.on_join)
        bot.events.on("received").on("part").hook(self.on_part)
        bot.events.on("received").on("quit").hook(self.on_quit)
        bot.events.on("received").on("nick").hook(self.on_nick)

    def print_line(self, event, line):
        timestamp = datetime.datetime.now().isoformat()
        target = str(event["server"])
        if "channel" in event:
            target += event["channel"].name
        print("[%s] %s | %s" % (timestamp, target, line))
    def on_message(self, event):
        if not self.bot.args.verbose:
            if event["action"]:
                self.print_line(event, "* %s %s" % (event["user"].nickname, event["message"]))
            else:
                self.print_line(event, "<%s> %s" % (event["user"].nickname, event["message"]))
    def on_join(self, event):
        if not self.bot.args.verbose:
            self.print_line(event, "%s joined %s" % (event["user"].nickname, event["channel"].name))
    def on_part(self, event):
        if not self.bot.args.verbose:
            self.print_line(event, "%s left %s%s" % (event["user"].nickname, event["channel"].name, "" if not event["reason"] else ": %s" % event["reason"]))
    def on_quit(self, event):
        if not self.bot.args.verbose:
            self.print_line(event, "%s quit" % event["user"].nickname)
    def on_nick(self, event):
        if not self.bot.args.verbose:
            self.print_line(event, "%s changed nickname to %s" % (event["old_nickname"], event["new_nickname"]))
