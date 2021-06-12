from src import IRCLine, ModuleManager, utils

TAG = utils.irc.MessageTag("msgid", "draft/msgid")
CAP = utils.irc.Capability("message-tags", "draft/message-tags-0.2")

class Module(ModuleManager.BaseModule):
    def _tagmsg(self, target, msgid, reaction):
        return IRCLine.ParsedLine("TAGMSG", [target],
            tags={
                "+draft/reply": msgid,
                "+draft/react": reaction
            })
    def _has_tags(self, server):
        return server.has_capability(CAP)

    def _expect_output(self, event):
        kwarg = event["hook"].get_kwarg("expect_output", None)
        return kwarg if not kwarg is None else event["expect_output"]

    @utils.hook("preprocess.command")
    def preprocess(self, event):
        if self._has_tags(event["server"]) and self._expect_output(event):
            msgid = TAG.get_value(event["line"].tags)
            if msgid:
                event["server"].send(self._tagmsg(event["target_str"], msgid, "👍"),
                    immediate=True)
