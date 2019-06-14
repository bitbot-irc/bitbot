#--depends-on commands

from src import ModuleManager, utils

LOWHIGH = {
    "low": "v",
    "high": "o"
}
@utils.export("channelset", {"setting": "mode-low",
    "help": "Set which channel mode is considered to be 'low' access",
    "example": "v"})
@utils.export("channelset", {"setting": "mode-high",
    "help": "Set which channel mode is considered to be 'high' access",
    "example": "o"})
class Module(ModuleManager.BaseModule):
    def _check_command(self, event, require_mode):
        if event["is_channel"] and require_mode:
            if require_mode.lower() in LOWHIGH:
                require_mode = event["target"].get_setting(
                    "mode-%s" % require_mode.lower(),
                    LOWHIGH[require_mode.lower()])

            if not event["target"].mode_or_above(event["user"],
                    require_mode):
                return "You do not have permission to do this"
            else:
                return utils.consts.PERMISSION_FORCE_SUCCESS

    @utils.hook("preprocess.command")
    def preprocess_command(self, event):
        require_mode = event["hook"].get_kwarg("require_mode")
        if not require_mode == None:
            return self._check_command(event, require_mode)

    @utils.hook("check.command.channel-mode")
    def check_command(self, event):
        return self._check_command(event, event["check_args"][0])
