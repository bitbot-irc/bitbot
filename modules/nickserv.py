import base64
from src import EventManager, ModuleManager, utils

@utils.export("serverset", {"setting": "nickserv-password",
    "help": "Set the nickserv password for this server"})
class Module(ModuleManager.BaseModule):
    @utils.hook("received.numeric.001", priority=EventManager.PRIORITY_URGENT)
    def on_connect(self, event):
        nickserv_password = event["server"].get_setting("nickserv-password")
        if nickserv_password:
            event["server"].attempted_auth = True
            event["server"].send_message("nickserv",
                "identify %s" % nickserv_password)
