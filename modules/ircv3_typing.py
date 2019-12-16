from bitbot import IRCLine, ModuleManager, utils

CAP = utils.irc.Capability("message-tags", "draft/message-tags-0.2")

class Module(ModuleManager.BaseModule):
    def _tagmsg(self, target, state):
        return IRCLine.ParsedLine("TAGMSG", [target],
            tags={"+draft/typing": state})
    def _has_tags(self, server):
        return server.has_capability(CAP)

    @utils.hook("preprocess.command")
    def preprocess(self, event):
        if (self._has_tags(event["server"]) and
                event["hook"].get_kwarg("expect_output", True)):
            event["target"]._typing = True
            event["server"].send(self._tagmsg(event["target_str"], "active"),
                immediate=True)
        else:
            event["target"]._typing = False

    @utils.hook("postprocess.command")
    def postprocess(self, event):
        if (event["target"]._typing and
                not event["stdout"].has_text() and
                not event["stderr"].has_text()):
            event["server"].send(self._tagmsg(event["target_str"], "done"))
