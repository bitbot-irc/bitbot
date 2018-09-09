import base64
import EventManager

class Module(object):
    def __init__(self, bot, events, exports):
        events.on("received").on("numeric").on("001").hook(self.on_connect,
            priority=EventManager.PRIORITY_URGENT)

        exports.add("serverset", {"setting": "nickserv-password",
            "help": "Set the nickserv password for this server"})

    def on_connect(self, event):
        nickserv_password = event["server"].get_setting(
            "nickserv-password")
        if nickserv_password:
            event["server"].attempted_auth = True
            event["server"].send_message("nickserv",
                "identify %s" % nickserv_password)
