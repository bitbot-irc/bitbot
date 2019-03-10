from src import ModuleManager, utils

@utils.export("serverset", {"setting": "strip-color",
    "help": "Set whether I strip colors from my messages on this server",
    "validate": utils.bool_or_none})
@utils.export("channelset", {"setting": "strip-color",
    "help": "Set whether I strip colors from my messages on in this channel",
    "validate": utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    @utils.hook("preprocess.send.privmsg")
    @utils.hook("preprocess.send.notice")
    def preprocess(self, event):
        strip_color = event["server"].get_setting("strip-color", False)
        target = event["line"].args[0]
        if not strip_color and target in event["server"].channels:
            channel = event["server"].channels.get(target)
            strip_color = channel.get_setting("strip-color", False)

        if strip_color:
            message = event["line"].args.get(-1)
            if not message == None:
                event["line"].args[-1] = utils.irc.strip_font(message)
