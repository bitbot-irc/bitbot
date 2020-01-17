from src import ModuleManager, utils

TAG = utils.irc.MessageTag("msgid", "draft/msgid")

class Module(ModuleManager.BaseModule):
    def _on_channel(self, channel, tags, buffer_line):
        msgid = TAG.get_value(tags)
        if not msgid == None:
            channel.set_setting("last-msgid", msgid)

            if buffer_line:
                buffer_line.id = msgid

    @utils.hook("received.message.channel")
    @utils.hook("send.message.channel")
    @utils.hook("received.notice.channel")
    @utils.hook("send.notice.channel")
    def on_channel(self, event):
        self._on_channel(event["channel"], event["tags"], event["buffer_line"])

    @utils.hook("received.tagmsg.channel")
    @utils.hook("send.tagmsg.channel")
    def tagmsg(self, event):
        self._on_channel(event["channel"], event["tags"], None)


    @utils.hook("received.ctcp.request")
    @utils.hook("received.ctcp.response")
    def ctcp(self, event):
        if event["is_channel"]:
            self._on_channel(event["target"], event["tags"], None)

    @utils.hook("postprocess.command")
    def postprocess_command(self, event):
        msgid = TAG.get_value(event["line"].tags)
        if msgid:
            event["tags"]["+draft/reply"] = msgid
            event["tags"]["+draft/reply"] = msgid
