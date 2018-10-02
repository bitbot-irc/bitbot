from src import ModuleManager, Utils

@Utils.export("serverset", {"setting": "strip-color",
    "help": "Set whether I strip colors from my messages on this server",
    "validate": Utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    @Utils.hook("preprocess.send")
    def preprocess(self, event):
        if event["server"].get_setting("strip-color", False):
            return Utils.strip_font(event["line"])
