#--depends-on config

from bitbot import ModuleManager, utils

@utils.export("serverset", utils.BoolSetting("strip-color",
    "Set whether I strip colors from my messages on this server"))
@utils.export("channelset", utils.BoolSetting("strip-color",
    "Set whether I strip colors from my messages on in this channel"))
class Module(ModuleManager.BaseModule):
    @utils.hook("preprocess.send.privmsg")
    @utils.hook("preprocess.send.notice")
    def preprocess(self, event):
        if len(event["line"].args) > 1:
            strip_color = event["server"].get_setting("strip-color", False)
            target = event["line"].args[0]
            if not strip_color and target in event["server"].channels:
                channel = event["server"].channels.get(target)
                strip_color = channel.get_setting("strip-color", False)

            if strip_color:
                message = event["line"].args[1]
                event["line"].args[1] = utils.irc.strip_font(message)
