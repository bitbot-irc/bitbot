#--depends-on config

from src import ModuleManager, utils

CAP = utils.irc.Capability("message-tags", "draft/message-tags-0.2")

@utils.export("channelset", utils.Setting("greeting",
    "Set a greeting to send to users when they join",
    example="welcome to the channel!"))
class Module(ModuleManager.BaseModule):
    @utils.hook("received.join")
    def join(self, event):
        greeting = event["channel"].get_setting("greeting", None)
        if greeting:
            tags = {}
            if event["server"].has_capability(CAP):
                tags["+draft/channel-context"] = event["channel"].name

            event["user"].send_notice("[%s] %s" % (event["channel"].name,
                greeting), tags)
