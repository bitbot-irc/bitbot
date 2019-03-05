import datetime
from src import EventManager, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _print_line(self, target, context, line):
        formatted_line = utils.irc.parse_format(line)
        self.bot.log.info("%s%s | %s", [target, context or "", formatted_line])

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
        self._print_line(str(event["server"]), event["context"], event["line"])
