
from src import ModuleManager, Utils

class Module(ModuleManager.BaseModule):
    @Utils.hook("preprocess.command")
    def preprocess_command(self, event):
        require_mode = event["hook"].get_kwarg("require_mode")
        if event["is_channel"] and require_mode:
            if not event["target"].mode_or_above(event["user"],
                    required_mode):
                return "You do not have permission to do this"
