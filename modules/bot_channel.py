from src import Utils

class Module(object):
    def __init__(self, bot, events, exports):
        exports.add("serverset", {"setting": "bot-channel",
            "help": "Set main channel"})

    @Utils.hook("received.numeric.001")
    def do_join(self, event):
        event["server"].send_join(event["server"].get_setting("bot-channel",
            "#bitbot"))
