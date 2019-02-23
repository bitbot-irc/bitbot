from src import ModuleManager, utils

@utils.export("serverset", {"setting": "strip-color",
    "help": "Set whether I strip colors from my messages on this server",
    "validate": utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    @utils.hook("preprocess.send.privmsg")
    @utils.hook("preprocess.send.notice")
    def preprocess(self, event):
        if event["server"].get_setting("strip-color", False):
            line = event["line"]
            line.args[-1] = utils.irc.strip_font(line.args[-1])
