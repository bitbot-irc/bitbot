from src import IRCBot, ModuleManager, utils

CAP = utils.irc.Capability(None, "draft/metadata")

class Module(ModuleManager.BaseModule):
    @utils.hook("received.cap.new")
    @utils.hook("received.cap.ls")
    def on_cap(self, event):
        cap = CAP.copy()
        if cap.available(event["capabilities"]):
            cap.on_ack(lambda: self._ack(event["server"]))
            return cap

    def _ack(self, server):
        url = self.bot.get_setting("bot-url", IRCBot.SOURCE)
        server.send_raw("METADATA * SET bot BitBot")
        server.send_raw("METADATA * SET homepage :%s" % url)
