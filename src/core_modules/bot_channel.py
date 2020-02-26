#--depends-on config

from src import ModuleManager, utils

@utils.export("serverset", utils.Setting("bot-channel",
    "Set main channel", example="#bitbot"))
class Module(ModuleManager.BaseModule):
    @utils.hook("received.001")
    def do_join(self, event):
        bot_channel = event["server"].get_setting("bot-channel",
            self.bot.config.get("bot-channel", None))
        if not bot_channel == None:
            event["server"].send_join(bot_channel)
