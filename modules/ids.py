from src import ModuleManager, Utils

class Module(ModuleManager.BaseModule):
    _name = "IDs"

    @Utils.hook("received.command.myid")
    def my_id(self, event):
        """
        Show your user ID
        """
        event["stdout"].write("%s: %d" % (event["user"].nickname,
            event["user"].get_id()))

    @Utils.hook("received.command.channelid", channel_only=True)
    def channel_id(self, event):
        """
        Show the current channel's ID
        """
        event["stdout"].write("%s: %d" % (event["target"].name,
            event["target"].id))
