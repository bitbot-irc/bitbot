import Utils

class Module(object):
    def __init__(self, bot, events, exports):
        pass

    @Utils.hook("received.command.ping", help="Ping pong!")
    def pong(self, event):
        event["stdout"].write("Pong!")
