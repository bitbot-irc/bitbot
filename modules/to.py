import EventManager

class Module(object):
    def __init__(self, bot):
        bot.events.on("received").on("message").on("channel"
            ).hook(self.channel_message,
            priority=EventManager.PRIORITY_MEDIUM)
        bot.events.on("received").on("command").on("to").hook(
            self.to, min_args=2, help=("Relay a message to a "
            "user the next time they talk in a channel"),
            channel_only=True, usage="<username> <message>")

    def channel_message(self, event):
        messages = event["channel"].get_user_setting(event["user"].id,
            "to", [])
        for nickname, message in messages:
            event["channel"].send_message("%s: <%s> %s" % (
                event["user"].nickname, nickname, message))
        if messages:
            event["channel"].del_user_setting(event["user"].id, "to")

    def to(self, event):
        target_user = event["server"].get_user(event["args_split"][0])
        messages = event["target"].get_user_setting(target_user.id,
            "to", [])
        messages.append([event["user"].nickname,
            " ".join(event["args_split"][1:])])
        event["target"].set_user_setting(target_user.id,
            "to", messages)
        event["stdout"].write("Message saved")
