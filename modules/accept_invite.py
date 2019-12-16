#--depends-on config

from bitbot import ModuleManager, utils

@utils.export("serverset", utils.BoolSetting("accept-invites",
    "Set whether I accept invites on this server"))
class Module(ModuleManager.BaseModule):
    @utils.hook("received.invite")
    def on_invite(self, event):
        if event["server"].is_own_nickname(event["target_user"].nickname):
            if event["server"].get_setting("accept-invites", True):
                event["server"].send_join(event["target_channel"])

