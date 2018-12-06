from src import ModuleManager, utils

@utils.export("serverset", {"setting": "bot-channel",
    "help": "Set main channel"})
class Module(ModuleManager.BaseModule):
    @utils.hook("received.numeric.001")
    def do_join(self, event):
        bot_channel = event["server"].get_setting("bot-channel",
            self.bot.config.get("bot-channel", "#bitbot"))
        event["server"].send_join(bot_channel)
