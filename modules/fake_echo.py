from src import EventManager, IRCLine, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("raw.send.privmsg", priority=EventManager.PRIORITY_MONITOR)
    @utils.hook("raw.send.notice", priority=EventManager.PRIORITY_MONITOR)
    def send_message(self, event):
        our_hostmask = utils.irc.parse_hostmask(event["server"].hostmask())

        echo = IRCLine.ParsedLine(event["line"].command, event["line"].args,
            source=our_hostmask, tags=event["line"].tags)
        echo.id = event["line"].id

        self.events.on("raw.received").call(line=echo, server=event["server"])
