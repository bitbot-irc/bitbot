#--depends-on commands
#--depends-on config

from bitbot import ModuleManager, utils

@utils.export("channelset", utils.BoolSetting("op-ping",
    "Enable/disable command that highlights all online channel ops"))
class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.ops")
    @utils.kwarg("channel_only", True)
    @utils.kwarg("help", "Alert the ops in the current channel")
    def ops(self, event):
        if event["target"].get_setting("op-ping", False):
            ops = []
            for user in event["target"].users:
                if event["target"].mode_or_above(user, "o"):
                    ops.append(user.nickname)
            if ops:
                event["stdout"].write(" ".join(ops))

