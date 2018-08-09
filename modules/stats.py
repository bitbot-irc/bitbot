import time

class Module(object):
    def __init__(self, bot):
        self.boot_time = time.time()
        self.bot = bot
        bot.events.on("received").on("command").on("uptime"
            ).hook(self.uptime, help="Show my uptime")
        bot.events.on("received").on("command").on("stats"
            ).hook(self.stats, help="Show my network/channel/user stats")

    def uptime(self, event):
        seconds = int(time.time()-self.boot_time)
        minutes = int(seconds/60)
        if not minutes:
            event["stdout"].write("Uptime: %s seconds" % seconds)
            return
        hours, minutes = int(minutes/60), int(minutes%60)
        days, hours = int(hours/24), int(hours%24)

        days_str = ""
        hours_str = "00"
        minutes_str = "00"
        if days:
            days_str = "days "
        if hours:
            hours_str = str(hours).zfill(2)
        if minutes:
            minutes_str = str(minutes).zfill(2)
        event["stdout"].write("Uptime: %s%s:%s" % (days_str, hours_str,
            minutes_str))

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
