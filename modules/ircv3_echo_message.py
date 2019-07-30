from src import EventManager, ModuleManager, utils

CAP = utils.irc.Capability("echo-message", depends_on=["labeled-response"])

@utils.export("cap", CAP)
class Module(ModuleManager.BaseModule):
    @utils.hook("raw.send.privmsg", priority=EventManager.PRIORITY_HIGH)
    @utils.hook("raw.send.notice", priority=EventManager.PRIORITY_HIGH)
    def send_message(self, event):
        if event["server"].has_capability(CAP):
            event.eat()

    @utils.hook("preprocess.send.privmsg")
    @utils.hook("preprocess.send.notice")
    @utils.hook("preprocess.send.tagmsg")
    def preprocess_send(self, event):
        if event["server"].has_capability(CAP):
            event["events"].on("labeled-response").hook(self.on_echo)

    def on_echo(self, event):
        event["responses"][0].id = event["line"].id
