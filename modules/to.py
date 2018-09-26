from src import EventManager, ModuleManager, Utils

class Module(ModuleManager.BaseModule):
    @Utils.hook("received.message.channel", priority=EventManager.PRIORITY_HIGH)
    def channel_message(self, event):
        messages = event["channel"].get_user_setting(event["user"].get_id(),
            "to", [])
        for nickname, message in messages:
            event["channel"].send_message("%s: <%s> %s" % (
                event["user"].nickname, nickname, message))
        if messages:
            event["channel"].del_user_setting(event["user"].get_id(), "to")

    @Utils.hook("received.command.to", min_args=2, channel_only=True,
        usage="<username> <message>")
    def to(self, event):
        """
        Relay a message to a user the next time they talk in this channel"
        """
        target_user = event["server"].get_user(event["args_split"][0])
        messages = event["target"].get_user_setting(target_user.get_id(),
            "to", [])
        messages.append([event["user"].nickname,
            " ".join(event["args_split"][1:])])
        event["target"].set_user_setting(target_user.get_id(),
            "to", messages)
        event["stdout"].write("Message saved")
