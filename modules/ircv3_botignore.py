from src import EventManager, ModuleManager, utils

TAGS = {
    utils.irc.MessageTag(None, "inspircd.org/bot"),
    utils.irc.MessageTag(None, "draft/bot")
}

class Module(ModuleManager.BaseModule):
    @utils.hook("received.376")
    @utils.hook("received.422")
    def botmode(self, event):
        if "BOT" in event["server"].isupport:
            botmode = event["server"].isupport["BOT"]
            event["server"].send_raw("MODE %s +%s" % (event["server"].nickname, botmode))

    @utils.hook("received.message.private")
    @utils.hook("received.message.channel")
    @utils.kwarg("priority", EventManager.PRIORITY_HIGH)
    def message(self, event):
        for tag in TAGS:
            if tag.present(event["tags"]):
                event.eat()
