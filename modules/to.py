from src import EventManager, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.message.channel", priority=EventManager.PRIORITY_HIGH)
    def channel_message(self, event):
        messages = event["channel"].get_user_setting(event["user"].get_id(),
            "to", [])
        for nickname, message in messages:
            event["channel"].send_message("%s: <%s> %s" % (
                event["user"].nickname, nickname, message))
        if messages:
            event["channel"].del_user_setting(event["user"].get_id(), "to")

    @utils.hook("received.command.to", min_args=2, channel_only=True)
    def to(self, event):
        """
        :help: Relay a message to a user the next time they talk in this
            channel
        :usage: <nickname> <message>
        """
        target_user = event["server"].get_user(event["args_split"][0])
        messages = event["target"].get_user_setting(target_user.get_id(),
            "to", [])
        messages.append([event["user"].nickname,
            " ".join(event["args_split"][1:])])
        event["target"].set_user_setting(target_user.get_id(),
            "to", messages)
        event["stdout"].write("Message saved")
