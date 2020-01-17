from src import ModuleManager, utils

DELETE_TAG = utils.irc.MessageTag(None, "draft/delete")

class Module(ModuleManager.BaseModule):
    @utils.hook("received.tagmsg.private")
    @utils.hook("received.tagmsg.channel")
    def tagmsg(self, event):
        msgid = DELETE_TAG.get_value(event["line"].tags)
        if msgid:
            line = event["target"].buffer.find_id(msgid)
            if line:
                line.deleted = True
