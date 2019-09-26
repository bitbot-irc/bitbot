#--depends-on commands

from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.echo")
    @utils.kwarg("min_args", 1)
    def echo(self, event):
        event["stdout"].write(event["args"])
