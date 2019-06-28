#--depends-on commands

from src import ModuleManager, utils

LOWHIGH = {
    "low": "v",
    "high": "o"
}

@utils.export("channelset", utils.Setting("mode-low",
    "Set which channel mode is considered to be 'low' access", example="v"))
@utils.export("channelset", utils.Setting("mode-high",
    "Set which channel mode is considered to be 'high' access", example="o"))
class Module(ModuleManager.BaseModule):
    def _check_command(self, event, channel, require_mode):
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
            return self._check_command(event, event["target"], require_mode)

    @utils.hook("check.command.channel-mode")
    def check_command(self, event):
        target = event["target"]
        mode = event["request_args"][0]
        if len(event["request_args"]) > 1:
            target = event["request_args"][0]
            mode = event["request_args"][1]

        return self._check_command(event, target, mode)
