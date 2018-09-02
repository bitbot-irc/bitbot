

class Module(object):
    def __init__(self, bot, events, exports):
        events.on("received.command.ping").hook(self.pong, help="Ping pong!")

    def pong(self, event):
        event["stdout"].write("Pong!")
