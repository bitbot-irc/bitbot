from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _done_connecting(self, server):
        target_nick = server.connection_params.nickname
        if not server.irc_equals(server.nickname, target_nick):
            if "MONITOR" in server.isupport:
                server.send_raw("MONITOR + %s" % target_nick)
            else:
                self.timers.add("ison-check", self._ison_check, 30,
                    server=server)

    @utils.hook("received.376")
    def end_of_motd(self, event):
        self._done_connecting(event["server"])
    @utils.hook("received.422")
    def no_motd(self, event):
        self._done_connecting(event["server"])

    @utils.hook("self.nick")
    def self_nick(self, event):
        target_nick = event["server"].connection_params.nickname
        if event["server"].irc_equals(event["new_nickname"], target_nick):
            if "MONITOR" in event["server"].isupport:
                event["server"].send_raw("MONITOR - %s " % target_nick)

    @utils.hook("received.731")
    def mon_offline(self, event):
        target_nick = event["server"].connection_params.nickname
        nicks = event["line"].args[1].split(",")
        nicks = [event["server"].irc_lower(n) for n in nicks]
        if event["server"].irc_lower(target_nick) in nicks:
            event["server"].send_nick(target_nick)

    def _ison_check(self, timer):
        server = timer.kwargs["server"]
        target_nick = server.connection_params.nickname
        if not server.irc_equals(server.nickname, target_nick):
            server.send_raw("ISON %s" % target_nick)
            timer.redo()

    @utils.hook("received.303")
    def ison_response(self, event):
        target_nick = event["server"].connection_params.nickname
        if not event["line"].args[1] and not event["server"].irc_equals(
                event["server"].nickname, target_nick):
            event["server"].send_nick(target_nick)

