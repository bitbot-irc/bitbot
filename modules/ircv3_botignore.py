from bitbot import EventManager, ModuleManager, utils

TAG = utils.irc.MessageTag(None, "inspircd.org/bot")

class Module(ModuleManager.BaseModule):
    @utils.hook("received.message.private")
    @utils.hook("received.message.channel")
    @utils.kwarg("priority", EventManager.PRIORITY_HIGH)
    def message(self, event):
        if TAG.present(event["tags"]):
            event.eat()
