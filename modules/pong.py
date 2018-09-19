import ModuleManager, Utils

class Module(ModuleManager.BaseModule):
    @Utils.hook("received.command.ping", help="Ping pong!")
    def pong(self, event):
        event["stdout"].write("Pong!")
