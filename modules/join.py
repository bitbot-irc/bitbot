

class Module(object):
    def __init__(self, bot, events):
        events.on("received").on("numeric").on("001").hook(self.do_join)

    def do_join(self, event):
        event["server"].send_join("#bitbot")
