from src import ModuleManager, utils

CAP = utils.irc.Capability("server-time")
TAG = utils.irc.MessageTag("time")

class Module(ModuleManager.BaseModule):
    @utils.hook("received.cap.ls")
    @utils.hook("received.cap.new")
    def on_cap(self, event):
        return CAP.copy()

    @utils.hook("raw.received")
    def raw_recv(self, event):
        server_time = TAG.get_value(event["line"].tags)
        if not server_time == None:
            event["server"].set_setting("last-server-time", server_time)
