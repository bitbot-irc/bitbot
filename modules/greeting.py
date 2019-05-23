from src import ModuleManager, utils

@utils.export("channelset", {"setting": "greeting",
    "help": "Set a greeting to send to users when they join",
    "example": "welcome to the channel!"})
class Module(ModuleManager.BaseModule):
    @utils.hook("received.join")
    def join(self, event):
        greeting = event["channel"].get_setting("greeting", None)
        if greeting:
            event["user"].send_notice("[%s] %s" % (event["channel"].name,
                greeting))
