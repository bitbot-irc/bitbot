from src import ModuleManager, utils

CAP = utils.irc.Capability("server-time")
TAG = utils.irc.MessageTag("time")

@utils.export("cap", CAP)
class Module(ModuleManager.BaseModule):
    def _get(self, tags):
        return TAG.get_value(tags)

    @utils.hook("raw.received")
    def raw_recv(self, event):
        server_time = self._get(event["line"].tags)
        if not server_time == None:
            event["server"].set_setting("last-server-time", server_time)

    @utils.hook("received.message.private")
    @utils.hook("received.message.channel")
    @utils.hook("received.notice.private")
    @utils.hook("received.notice.channel")
    def message(self, event):
        server_time = self._get(event["line"].tags)
        if not server_time == None:
            dt = utils.datetime.iso8601_parse(server_time)
            event["buffer_line"].timestamp = dt
