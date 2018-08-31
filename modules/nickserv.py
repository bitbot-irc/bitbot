import base64
import EventManager

class Module(object):
    def __init__(self, bot, events):
        events.on("received").on("numeric").on("001"
            ).hook(self.on_connect, priority=EventManager.PRIORITY_URGENT)
        events.on("received").on("command").on("setnickserv"
            ).hook(self.set_nickserv, min_args=1, permission="setnickserv",
            help="Set bot's nickserv password", usage="<password>",
            private_only=True)

    def on_connect(self, event):
        nickserv_password = event["server"].get_setting(
            "nickserv-password")
        if nickserv_password:
            event["server"].attempted_auth = True
            event["server"].send_message("nickserv",
                "identify %s" % nickserv_password)

    def set_nickserv(self, event):
        nickserv_password = event["args"]
        event["server"].set_setting("nickserv-password", nickserv_password)
        event["stdout"].write("Nickserv password saved")
