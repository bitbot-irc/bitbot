from bitbot import ModuleManager, utils

MSGID_TAG = "draft/msgid"
READ_TAG = "+draft/read"
DELIVERED_TAG = "+draft/delivered"
MESSAGE_TAG_CAPS = set(["draft/message-tags-0.2", "message-tags"])

class Module(ModuleManager.BaseModule):
    @utils.hook("received.message.private")
    @utils.hook("received.notice.private")
    def privmsg(self, event):
        if MSGID_TAG in event["tags"] and (
                event["server"].agreed_capabilities & MESSAGE_TAG_CAPS):
            target = event.get("channel", event["user"])
            msgid = event["tags"][MSGID_TAG]
            tags = {DELIVERED_TAG: msgid, READ_TAG: msgid}
            target.send_tagmsg(tags)
