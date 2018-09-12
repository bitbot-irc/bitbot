

class Module(object):
    def __init__(self, bot, events, exports):
        events.on("received").on("numeric").on("001").hook(self.do_join)

        exports.add("serverset", {"setting": "bot-channel",
            "help": "Set main channel"})

    def do_join(self, event):
        event["server"].send_join(event["server"].get_setting("bot-channel",
            "#bitbot"))
