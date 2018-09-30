from src import ModuleManager, Utils

class Module(ModuleManager.BaseModule):
    @Utils.hook("received.command.ping")
    def pong(self, event):
        """
        :help: Ping pong!
        """
        event["stdout"].write("Pong!")
