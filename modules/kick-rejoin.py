#--depends-on config

from src import ModuleManager, utils

DELAY = 5

@utils.export("serverset", utils.BoolSetting("kick-rejoin",
    "Whether or not I should rejoin channels I get kicked from"))
@utils.export("serverset", utils.IntSetting("kick-rejoin-delay",
    "Amount of seconds to wait before rejoining a channel"))
class Module(ModuleManager.BaseModule):
    @utils.hook("self.kick")
    def on_kick(self, event):
        if event["server"].get_setting("kick-rejoin", False):
            delay = event["server"].get_setting("kick-rejoin-delay", DELAY)
            self.timers.add("kick-rejoin", delay, server=event["server"],
                channel_name=event["channel"].name)

    @utils.hook("timer.kick-rejoin")
    def timer(self, event):
        event["server"].send_join(event["channel_name"])
