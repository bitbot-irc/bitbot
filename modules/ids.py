

class Module(object):
    _name = "IDs"
    def __init__(self, bot):
        bot.events.on("received.command.myid").hook(self.my_id,
            help="Show your user ID")
        bot.events.on("received.command.channelid").hook(
            self.channel_id, channel_only=True,
            help="Show the current channel's ID")

    def my_id(self, event):
        event["stdout"].write("%s: %d" % (event["user"].nickname,
            event["user"].id))

    def channel_id(self, event):
        event["stdout"].write("%s: %d" % (event["target"].name,
            event["target"].id))
