from src import ModuleManager, utils

CAP = utils.irc.Capability(None, "bitbot.dev/multi-line")

class Module(ModuleManager.BaseModule):
    @utils.hook("received.cap.ls")
    @utils.hook("received.cap.new")
    def on_cap(self, event):
        if CAP.available(event["capabilities"]):
            return CAP.copy()

    @utils.hook("preprocess.send.privmsg")
    def preprocess_send_privmsg(self, event):
        if len(event["line"].args) > 1:
            if ("\n" in event["line"].args[1] and
                    event["server"].has_capability(CAP)):
                event["line"].invalidate()

                target = event["line"].args[0]
                lines = event["line"].args[1].split("\n")
                batch = utils.irc.IRCSendBatch("bitbot.dev/multi-line",
                    [target])
                for line in lines:
                    batch.add_line(utils.irc.protocol.privmsg(target, line))
                for line in batch.get_lines():
                    event["server"].send(line)
