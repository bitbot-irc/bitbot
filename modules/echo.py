#--depends-on commands

from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.echo")
    @utils.kwarg("min_args", 1)
    def echo(self, event):
        event["stdout"].write(event["args"])

    @utils.hook("received.command.action")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("expect_output", False)
    def action(self, event):
        event["target"].send_message("\x01ACTION %s\x01" % event["args"])
