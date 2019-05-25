#--depends-on commands

from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    _name = "IDs"

    @utils.hook("received.command.myid")
    def my_id(self, event):
        """
        :help: Show your user ID
        """
        event["stdout"].write("%s: %d" % (event["user"].nickname,
            event["user"].get_id()))

    @utils.hook("received.command.channelid", channel_only=True)
    def channel_id(self, event):
        """
        :help: Show the current channel's ID
        """
        event["stdout"].write("%s: %d" % (event["target"].name,
            event["target"].id))
