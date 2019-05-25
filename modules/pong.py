#--depends-on commands

from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.ping")
    def pong(self, event):
        """
        :help: Ping pong!
        """
        event["stdout"].write("Pong!")
