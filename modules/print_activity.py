#--depends-on config
#--depends-on format_activity

import datetime
from src import EventManager, ModuleManager, utils

@utils.export("botset",
    utils.BoolSetting("print-motd", "Set whether I print /motd"))
class Module(ModuleManager.BaseModule):
    def _print(self, event):
        self.bot.log.info("%s%s | %s", [
            str(event["server"]), event["context"] or "",
            utils.irc.parse_format(event["line"])])

    @utils.hook("formatted.message.channel")
    @utils.hook("formatted.notice.channel")
    @utils.hook("formatted.notice.private")
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
    @utils.hook("formatted.chghost")
    def formatted(self, event):
        self._print(event)

    @utils.hook("formatted.motd")
    def motd(self, event):
        if self.bot.get_setting("print-motd", True):
            self._print(event)
