#--depends-on commands

from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.echo")
    @utils.kwarg("remove_empty", False)
    @utils.kwarg("help", "Echo a string back")
    @utils.spec("!string")
    def echo(self, event):
        event["stdout"].write(event["spec"][0])

    @utils.hook("received.command.action")
    @utils.kwarg("remove_empty", False)
    @utils.kwarg("help", "Make the bot send a /me")
    @utils.spec("!string")
    def action(self, event):
        event["target"].send_message("\x01ACTION %s\x01" % event["spec"][0])

    @utils.hook("received.command.msg")
    @utils.kwarg("permission", "say")
    @utils.kwarg("remove_empty", False)
    @utils.kwarg("help", "Send a message to a target")
    @utils.spec("!word !string")
    def msg(self, event):
        event["server"].send_message(event["spec"][0], event["spec"][1])
