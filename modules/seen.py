import time
import Utils

class Module(object):
    def __init__(self, bot):
        bot.events.on("received").on("message").on("channel"
            ).hook(self.channel_message)
        bot.events.on("received").on("command").on("seen").hook(
            self.seen, min_args=1,
            help="Find out when a user was last seen",
            usage="<username>")

    def channel_message(self, event):
        seen_seconds = time.time()
        event["user"].set_setting("seen", seen_seconds)

    def seen(self, event):
        seen_seconds = event["server"].get_user(event["args_split"][0]
            ).get_setting("seen")
        if seen_seconds:
            since = Utils.to_pretty_time(time.time()-seen_seconds,
                max_units=2)
            event["stdout"].write("%s was last seen %s ago" % (
                event["args_split"][0], since))
        else:
            event["stderr"].write("I have never seen %s before." % (
                event["args_split"][0]))
