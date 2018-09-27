from src import ModuleManager, Utils

@Utils.export("channelset", {"setting": "greeting",
    "help": "Set a greeting to send to users when they join"})
class Module(ModuleManager.BaseModule):
    @Utils.hook("received.join")
    def join(self, event):
        greeting = event["channel"].get_setting("greeting", None)
        if greeting:
            event["user"].send_notice("[%s] %s" % (event["channel"].name,
                greeting))
