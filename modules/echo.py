#--depends-on commands

from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.echo")
    @utils.kwarg("remove_empty", False)
    @utils.kwarg("help", "Echo a string back")
    @utils.kwarg("spec", "!...")
    def echo(self, event):
        event["stdout"].write(event["spec"][0])

    @utils.hook("received.command.action")
    @utils.kwarg("remove_empty", False)
    @utils.kwarg("help", "Make the bot send a /me")
    @utils.kwarg("spec", "!...")
    def action(self, event):
        event["target"].send_message("\x01ACTION %s\x01" % event["spec"][0])

    @utils.hook("received.command.msg")
    @utils.kwarg("permission", "say")
    @utils.kwarg("remove_empty", False)
    @utils.kwarg("help", "Send a message to a target")
    @utils.kwarg("spec", "!word !...")
    def msg(self, event):
        event["server"].send_message(event["spec"][0], event["spec"][1])
