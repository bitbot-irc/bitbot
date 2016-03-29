import time
import Utils

class Module(object):
    def __init__(self, bot):
        bot.events.on("received").on("message").on("channel"
            ).hook(self.channel_message)
        bot.events.on("received").on("command").on("seen").hook(
            self.seen, min_args=1,
            help="Find out when a user was last seen")

    def channel_message(self, event):
        seen_seconds = time.time()
        event["user"].set_setting("seen", seen_seconds)

    def seen(self, event):
        seen_seconds = event["server"].get_user(event["args_split"][0]
            ).get_setting("seen")
        if seen_seconds:
            since, unit = Utils.time_unit(time.time()-seen_seconds)
            event["stdout"].write("%s was last seen %s %s ago" % (
                event["args_split"][0], since, unit))
        else:
            event["stderr"].write("I have never seen %s before." % (
                event["args_split"][0]))
