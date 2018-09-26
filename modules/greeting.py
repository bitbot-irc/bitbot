from src import Utils

class Module(object):
    def __init__(self, bot, events, exports):
        exports.add("channelset", {"setting": "greeting",
            "help": "Set a greeting to send to users when they join"})

    @Utils.hook("recevied.join")
    def join(self, event):
        greeting = event["channel"].get_setting("greeting", None)
        if greeting:
            event["user"].send_notice("[%s] %s" % (event["channel"].name,
                greeting))
