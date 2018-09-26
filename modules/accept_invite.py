from src import Utils

class Module(object):
    def __init__(self, bot, events, exports):
        exports.add("serverset", {"setting": "accept-invites",
            "help": "Set whether I accept invites on this server",
            "validate": Utils.bool_or_none})

    @Utils.hook("received.invite")
    def on_invite(self, event):
        if event["server"].is_own_nickname(event["target_user"].nickname):
            if event["server"].get_setting("accept-invites", True):
                event["server"].send_join(event["target_channel"])

