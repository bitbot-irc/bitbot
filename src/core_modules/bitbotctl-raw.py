#--depends-on commands

from src import IRCLine, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _id_from_alias(self, alias):
        return self.bot.database.servers.get_by_alias(alias)
    def _server_from_alias(self, alias):
        id, server = self._both_from_alias(alias)
        return server
    def _both_from_alias(self, alias):
        id = self._id_from_alias(alias)
        if id == None:
            raise utils.EventError("Unknown server alias")
        return id, self.bot.get_server_by_id(id)

    @utils.hook("control.raw")
    def rawctl(self, event):
        rawargs = str(event["data"]).split(" ", 1)
        server = self._server_from_alias(rawargs[0])
        if IRCLine.is_human(rawargs[1]):
            line = IRCLine.parse_human(rawargs[1])
        else:
            line = IRCLine.parse_line(rawargs[1])
        line = server.send(line)

        if not line == None:
            return "Sent: " + line.parsed_line.format()
        else:
            return "Line was filtered"
