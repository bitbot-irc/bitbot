import time
import Utils

class Module(object):
    def __init__(self, bot, events):
        self.boot_time = time.time()
        self.bot = bot
        events.on("received").on("command").on("uptime"
            ).hook(self.uptime, help="Show my uptime")
        events.on("received").on("command").on("stats"
            ).hook(self.stats, help="Show my network/channel/user stats")

    def uptime(self, event):
        seconds = int(time.time()-self.boot_time)
        event["stdout"].write("Uptime: %s" % Utils.to_pretty_time(
            seconds))

    def stats(self, event):
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
