import datetime
from src import EventManager, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("formatted.message.channel")
    @utils.hook("formatted.notice.channel")
    @utils.hook("formatted.join")
    @utils.hook("formatted.part")
    @utils.hook("formatted.nick")
    @utils.hook("formatted.server-notice")
    @utils.hook("formatted.invite")
    @utils.hook("formatted.mode.channel")
    @utils.hook("formatted.topic")
    @utils.hook("formatted.topic-timestamp")
    @utils.hook("formatted.kick")
    @utils.hook("formatted.quit")
    @utils.hook("formatted.rename")
    @utils.hook("formatted.motd")
    def formatted(self, event):
        self.bot.log.info("%s%s | %s", [
            str(event["server"]), event["context"] or "", event["line"]])
