

class Module(object):
    def __init__(self, bot, events, exports):
        events.on("received").on("invite").hook(self.on_invite)

    def on_invite(self, event):
        if event["server"].is_own_nickname(event["target_user"].nickname):
            if event["server"].get_setting("accept-invites", True):
                event["server"].send_join(event["target_channel"])
