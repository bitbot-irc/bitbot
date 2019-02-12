import datetime
from src import ModuleManager, utils

VERSION_DEFAULT = "BitBot (https://git.io/bitbot)"
SOURCE_DEFAULT = "https://git.io/bitbot"

@utils.export("serverset", {"setting": "ctcp-responses",
    "help": "Set whether I respond to CTCPs on this server",
    "validate": utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    @utils.hook("received.ctcp.version.private")
    def ctcp_version(self, event):
        event["user"].send_ctcp_response("VERSION",
            self.bot.config.get("ctcp-version", VERSION_DEFAULT))

    @utils.hook("received.ctcp.source.private")
    def ctcp_source(self, event):
        event["user"].send_ctcp_response("SOURCE",
            self.bot.config.get("ctcp-source", SOURCE_DEFAULT))

    @utils.hook("received.ctcp.ping.private")
    def ctcp_ping(self, event):
        event["user"].send_ctcp_response("PING", event["message"])

    @utils.hook("received.ctcp.time.private")
    def ctcp_time(self, event):
        event["user"].send_ctcp_response("TIME",
            datetme.datetime.now().strftime("%c"))
