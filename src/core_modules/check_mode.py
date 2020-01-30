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
        if channel:
            if require_mode in LOWHIGH:
                require_mode = channel.get_setting("mode-%s" % require_mode,
                    LOWHIGH[require_mode])
            elif require_mode == "admin":
                previous = None
                for mode, _ in event["server"].prefix_modes:
                    if mode == "o":
                        require_mode = previous or mone
                        break
                    previous = mode
            elif require_mode == "highest":
                require_mode = event["server"].prefix_modes[0][0]
            if not channel.mode_or_above(event["user"], require_mode):
                return (utils.consts.PERMISSION_ERROR,
                    "You do not have permission to do this")
            else:
                return utils.consts.PERMISSION_FORCE_SUCCESS, None
        else:
            raise ValueError("_command_check requires a channel")

    @utils.hook("preprocess.command")
    def preprocess_command(self, event):
        require_mode = event["hook"].get_kwarg("require_mode")
        if not require_mode == None:
            channel = event["kwargs"].get("channel",
                event["target"] if event["is_channel"] else None)
            return self._check_command(event, channel, require_mode)

    @utils.hook("check.command.channel-mode")
    def check_command(self, event):
        target = event["target"]
        mode = event["request_args"][0]
        if len(event["request_args"]) > 1:
            target = event["request_args"][0]
            mode = event["request_args"][1]

        return self._check_command(event, target, mode)
