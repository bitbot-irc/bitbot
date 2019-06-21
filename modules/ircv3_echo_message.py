from src import EventManager, ModuleManager, utils

CAP = utils.irc.Capability("echo-message", depends_on=["labeled-response"])

@utils.export("cap", CAP)
class Module(ModuleManager.BaseModule):
    @utils.hook("raw.send.privmsg", priority=EventManager.PRIORITY_LOW)
    @utils.hook("raw.send.notice", priority=EventManager.PRIORITY_LOW)
    def send_message(self, event):
        if event["server"].has_capability(CAP):
            event.eat()
