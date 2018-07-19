

class Module(object):
    def __init__(self, bot):
        bot.events.on("received").on("invite").hook(
            self.on_invite)

    def on_invite(self, event):
        if event["server"].get_setting("accept-invites", True):
            event["server"].send_join(event["target_channel"])
