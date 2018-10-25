from src import ModuleManager, utils

@utils.export("serverset", {"setting": "bot-channel",
    "help": "Set main channel"})
class Module(ModuleManager.BaseModule):
    @utils.hook("received.numeric.001")
    def do_join(self, event):
        event["server"].send_join(event["server"].get_setting("bot-channel",
            "#bitbot"))
