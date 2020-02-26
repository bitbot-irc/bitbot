#--depends-on config

from src import ModuleManager, utils

SETTING = utils.BoolSetting("accept-invites",
    "Set whether I accept invites")
@utils.export("botset", SETTING)
@utils.export("serverset", SETTING)
class Module(ModuleManager.BaseModule):
    @utils.hook("received.invite")
    def on_invite(self, event):
        if event["server"].is_own_nickname(event["target_user"].nickname):
            if event["server"].get_setting("accept-invites",
                    self.bot.get_setting("accept-invites", False)):
                event["server"].send_join(event["target_channel"])

