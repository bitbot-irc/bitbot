#--depends-on commands

from src import EventManager, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.message.channel", priority=EventManager.PRIORITY_HIGH)
    def channel_message(self, event):
        messages = event["channel"].get_user_setting(event["user"].get_id(),
            "to", [])
        for nickname, message, timestamp in messages:
            timestamp_parsed = utils.datetime.iso8601_parse(timestamp)
            timestamp_human = utils.datetime.datetime_human(timestamp_parsed)
            event["channel"].send_message("%s: <%s> %s (at %s UTC)" % (
                event["user"].nickname, nickname, message, timestamp_human))
        if messages:
            event["channel"].del_user_setting(event["user"].get_id(), "to")

    @utils.hook("received.command.to", alias_of="tell")
    @utils.hook("received.command.tell")
    @utils.kwarg("min_args", 2)
    @utils.kwarg("channel_only", True)
    @utils.kwarg("help",
        "Relay a message to a user the next time they talk in this channel")
    @utils.kwarg("usage", "<nickname> <message>")
    def tell(self, event):
        target_name = event["args_split"][0]
        if not event["server"].has_user_id(target_name):
            raise utils.EventError("I've never seen %s before" % target_name)

        target_user = event["server"].get_user(event["args_split"][0])
        messages = event["target"].get_user_setting(target_user.get_id(),
            "to", [])

        if len(messages) == 5:
            raise utils.EventError("Users can only have 5 messages stored")

        messages.append([event["user"].nickname,
            " ".join(event["args_split"][1:]),
            utils.datetime.iso8601_format_now()])
        event["target"].set_user_setting(target_user.get_id(),
            "to", messages)
        event["stdout"].write("Message saved")
