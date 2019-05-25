#--depends-on config

from src import ModuleManager, utils

@utils.export("serverset", {"setting": "accept-invites",
    "help": "Set whether I accept invites on this server",
    "validate": utils.bool_or_none, "example": "on"})
class Module(ModuleManager.BaseModule):
    @utils.hook("received.invite")
    def on_invite(self, event):
        if event["server"].is_own_nickname(event["target_user"].nickname):
            if event["server"].get_setting("accept-invites", True):
                event["server"].send_join(event["target_channel"])

