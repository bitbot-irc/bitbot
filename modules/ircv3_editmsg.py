from src import ModuleManager, utils

CAP = utils.irc.Capability(None, "draft/edit", alias="edit")
DELETE_TAG = utils.irc.MessageTag(None, "draft/delete")

@utils.export("cap", CAP)
class Module(ModuleManager.BaseModule):
    def _tagmsg(self, event, channel):
        msgid = DELETE_TAG.get_value(event["line"].tags)
        if msgid:
            line = event["target"].buffer.find_id(msgid)
            if line:
                line.deleted = True

                timestamp = utils.datetime.datetime_human(line.timestamp,
                    timespec=utils.datetime.TimeSpec.MILLISECOND)
                minimal = "{~NICK} deleted line from %s (%s)" % (
                    timestamp, line.message)
                line = "- %s" % minimal

                self.exports.get_one("format")("delete", event["server"], line,
                    event["target_str"], minimal=minimal, channel=channel,
                    user=event["user"])

    @utils.hook("received.tagmsg.private")
    def private(self, event):
        self._tagmsg(event, None)
    @utils.hook("received.tagmsg.channel")
    def channel(self, event):
        self._tagmsg(event, event["target"])
