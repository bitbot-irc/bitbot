from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.numeric.251")
    def on_connect(self, event):
        target_nick = event["server"].connection_params.nickname
        if not event["server"].irc_equals(
                event["server"].nickname, target_nick):
            if "MONITOR" in event["server"].isupport:
                event["server"].send("MONITOR + %s" % target_nick)
            else:
                self.timers.add("ison-check", 30, server=event["server"])

    @utils.hook("self.nick")
    def self_nick(self, event):
        target_nick = event["server"].connection_params.nickname
        if event["server"].irc_equals(event["new_nickname"], target_nick):
            if "MONITOR" in event["server"].isupport:
                event["server"].send("MONITOR - %s " % target_nick)

    @utils.hook("received.numeric.731")
    def mon_offline(self, event):
        target_nick = event["server"].connection_params.nickname
        nicks = event["args"][1].split(",")
        nicks = [event["server"].irc_lower(n) for n in nicks]
        if event["server"].irc_lower(target_nick) in nicks:
            event["server"].send_nick(target_nick)

    @utils.hook("timer.ison-check")
    def ison_check(self, event):
        target_nick = event["server"].connection_params.nickname
        if not event["server"].irc_equals(
                event["server"].nickname, target_nick):
            event["server"].send("ISON %s" % target_nick)
            event["timer"].redo()

    @utils.hook("received.numeric.303")
    def ison_response(self, event):
        target_nick = event["server"].connection_params.nickname
        if not event["args"][1] and not event["server"].irc_equals(
                event["server"].nickname, target_nick):
            event["server"].send_nick(target_nick)

