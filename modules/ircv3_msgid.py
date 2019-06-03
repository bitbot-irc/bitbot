from src import ModuleManager, utils

TAG = utils.irc.MessageTag("msgid", "draft/msgid")

class Module(ModuleManager.BaseModule):
    @utils.hook("received.message.channel")
    #TODO: catch CTCPs
    @utils.hook("received.notice.channel")
    @utils.hook("received.tagmsg.channel")
    def on_channel(self, event):
        msgid = TAG.get_value(event["tags"])
        if not msgid == None:
            event["channel"].set_setting("last-msgid", msgid)
