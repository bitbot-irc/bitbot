#--depends-on config

import datetime
from src import IRCBot, ModuleManager, utils


@utils.export("serverset", {"setting": "ctcp-responses",
    "help": "Set whether I respond to CTCPs on this server",
    "validate": utils.bool_or_none, "example": "on"})
class Module(ModuleManager.BaseModule):
    @utils.hook("received.ctcp.request.version")
    def ctcp_version(self, event):
        default = "BitBot %s (%s)" % (IRCBot.VERSION, IRCBot.SOURCE)

        event["user"].send_ctcp_response("VERSION",
            self.bot.config.get("ctcp-version", default))

    @utils.hook("received.ctcp.request.source")
    def ctcp_source(self, event):
        event["user"].send_ctcp_response("SOURCE",
            self.bot.config.get("ctcp-source", IRCBot.SOURCE))

    @utils.hook("received.ctcp.request.ping")
    def ctcp_ping(self, event):
        event["user"].send_ctcp_response("PING", event["message"])

    @utils.hook("received.ctcp.request.time")
    def ctcp_time(self, event):
        event["user"].send_ctcp_response("TIME",
            datetime.datetime.now().strftime("%c"))
