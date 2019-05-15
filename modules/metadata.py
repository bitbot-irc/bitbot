from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.cap.new")
    @utils.hook("received.cap.ls")
    def on_cap(self, event):
        cap = utils.irc.Capability(None, "draft/metadata")
        if cap.available(event["capabilities"]):
            cap.on_ack(lambda: self._ack(event["server"]))
            return cap

    def _cap(self, server):
        url = self.bot.get_setting("bot-url", IRCBot.SOURCE)
        server.send_raw("METADATA * SET bot-url :%s" % url)
