from src import IRCLine, ModuleManager, utils

CAP = utils.irc.Capability(None, "draft/multiline", alias="multiline")
BATCH = utils.irc.BatchType(None, "draft/multiline")
TAG = utils.irc.MessageTag(None, "draft/multiline-concat")

@utils.export("cap", CAP)
class Module(ModuleManager.BaseModule):
    @utils.hook("preprocess.send.privmsg")
    def preprocess_send_privmsg(self, event):
        if len(event["line"].args) > 1:
            if ("\n" in event["line"].args[1] and
                    event["server"].has_capability(CAP)):
                event["line"].invalidate()

                target = event["line"].args[0]
                lines = event["line"].args[1].split("\n")
                batch = IRCLine.IRCSendBatch("draft/multiline",
                    [target])
                for line in lines:
                    line = IRCLine.ParsedLine("PRIVMSG", [target, line])
                    batch.add_line(line)
                for line in batch.get_lines():
                    event["server"].send(line)

    @utils.hook("received.batch.end")
    def batch_end(self, event):
        if BATCH.match(event["batch"].type):
            messages = []
            lines = event["batch"].get_lines()
            for line in lines:
                message = line.args[1]
                if TAG.present(line.tags):
                    last_message = ""
                    if messages:
                        last_message = messages.pop(-1)
                    message = last_message+message
                messages.append(message)

            target = event["batch"].args[0]
            message = "\n".join(messages)
            return [IRCLine.ParsedLine("PRIVMSG", [target, message],
                source=event["batch"].source)]
