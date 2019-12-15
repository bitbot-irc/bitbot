from bitbot import ModuleManager, utils

COMMANDS = ["!botlist", "!rollcall"]
MESSAGE = "Hi! I'm BitBot (https://git.io/bitbot) "

@utils.export("botset", utils.BoolSetting("botlist",
    "Whether or not I should respond to !botlist commands"))
class Module(ModuleManager.BaseModule):
    @utils.hook("received.message.channel")
    def channel_message(self, event):
        if (event["message"].strip() in COMMANDS and
                self.bot.get_setting("botlist", False)):
            event["channel"].send_message(MESSAGE)
