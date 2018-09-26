import time
from src import Utils

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot

    @Utils.hook("received.command.uptime")
    def uptime(self, event):
        """
        Show my uptime
        """
        seconds = int(time.time()-self.bot.start_time)
        event["stdout"].write("Uptime: %s" % Utils.to_pretty_time(
            seconds))

    @Utils.hook("received.command.stats")
    def stats(self, event):
        """
        Show my network/channel/user stats
        """
        networks = len(self.bot.servers)
        channels = 0
        users = 0
        for server in self.bot.servers.values():
            channels += len(server.channels)
            users += len(server.users)


        response = "I currently have %d network" % networks
        if networks > 1:
            response += "s"
        response += ", %d channel" % channels
        if channels > 1:
            response += "s"
        response += " and %d visible user" % users
        if users > 1:
            response += "s"

        event["stdout"].write(response)
