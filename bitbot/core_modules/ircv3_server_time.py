from bitbot import ModuleManager, utils

CAP = utils.irc.Capability("server-time")
TAG = utils.irc.MessageTag("time")

@utils.export("cap", CAP)
class Module(ModuleManager.BaseModule):
    @utils.hook("raw.received")
    def raw_recv(self, event):
        server_time = TAG.get_value(event["line"].tags)
        if not server_time == None:
            event["server"].set_setting("last-server-time", server_time)
