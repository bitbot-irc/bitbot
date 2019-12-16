#--depends-on config

import base64
from bitbot import EventManager, ModuleManager, utils

@utils.export("serverset", utils.SensitiveSetting("nickserv-password",
    "Set the nickserv password for this server", example="hunter2"))
class Module(ModuleManager.BaseModule):
    @utils.hook("received.001", priority=EventManager.PRIORITY_URGENT)
    def on_connect(self, event):
        nickserv_password = event["server"].get_setting("nickserv-password")
        if nickserv_password:
            event["server"].send_message("nickserv",
                "identify %s" % nickserv_password)
