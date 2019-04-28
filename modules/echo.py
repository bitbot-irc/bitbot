from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.echo")
    def echo(self, event):
        event["stdout"].write(event["args"])
