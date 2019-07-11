#--depends-on config

from src import ModuleManager, utils

@utils.export("serverset", utils.BoolSetting("kick-rejoin",
    "Whether or not I should rejoin channels I get kicked from"))
class Module(ModuleManager.BaseModule):
    @utils.hook("self.kick")
    def on_kick(self, event):
        if event["server"].get_setting("kick-rejoin", False):
            event["server"].send_join(event["channel"].name)
