

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("channel").on("mode").hook(self.on_mode)
        bot.events.on("received").on("join").hook(self.on_join)

    def on_mode(self, event):
        if event["channel"].get_setting("auto-mode", False):
            remove = event["remove"]
            channel = event["channel"]
            mode = event["mode"]
            args = event["args"]

    def on_join(self, event):
        if event["channel"].get_setting("auto-mode", False):
            pass
