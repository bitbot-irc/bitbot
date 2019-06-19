from src import ModuleManager, utils

TAG = utils.irc.MessageTag(None, "inspircd.org/bot")

class Module(ModuleManager.BaseModule):
    @utils.hook("received.message.private")
    @utils.hook("received.message.channel")
    def message(self, event):
        if TAG.present(event["tags"]):
            event.eat()
