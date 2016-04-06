

class Module(object):
    def __init__(self, bot):
        bot.events.on("received").on("message").on("channel"
            ).hook(self.channel_message)
        bot.events.on("received").on("command").on("to").hook(
            self.to, min_args=2, help=("Relay a message to a "
            "user the next time they talk in a channel"),
            channel_only=True, usage="<username> <message>")

    def channel_message(self, event):
        setting = "to-%s" % event["user"].nickname
        messages = event["channel"].get_setting(setting, [])
        for nickname, message in messages:
            event["channel"].send_message("%s: <%s> %s" % (
                event["user"].nickname, nickname, message))
        event["channel"].del_setting(setting)

    def to(self, event):
        setting = "to-%s" % event["args_split"][0]
        messages = event["target"].get_setting(setting, [])
        messages.append([event["user"].nickname,
            " ".join(event["args_split"][1:])])
        event["target"].set_setting(setting, messages)
        event["stdout"].write("Message saved")
