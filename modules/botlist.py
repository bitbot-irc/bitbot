from src import ModuleManager, utils

COMMANDS = ["!botlist", "!rollcall"]
MESSAGE = "Hi! I'm BitBot (https://git.io/bitbot) "

class Module(ModuleManager.BaseModule):
    @utils.hook("received.message.channel")
    def channel_message(self, event):
        if event["message"].strip() in COMMANDS:
            event["channel"].send_message(MESSAGE)
