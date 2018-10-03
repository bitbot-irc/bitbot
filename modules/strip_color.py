from src import ModuleManager, utils

@utils.export("serverset", {"setting": "strip-color",
    "help": "Set whether I strip colors from my messages on this server",
    "validate": utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    @utils.hook("preprocess.send")
    def preprocess(self, event):
        if event["server"].get_setting("strip-color", False):
            return utils.irc.strip_font(event["line"])
