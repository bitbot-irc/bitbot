import os, socket
from src import Socket

class ControlSocket(object):
    def __init__(self, bot):
        self.bot = bot

        location = bot.config["control-socket"]
        if os.path.exists(location):
            os.unlink(location)
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(location)
        self.socket.listen()
        self.connected = True

    def fileno(self):
        return self.socket.fileno()
    def waiting_send(self):
        return False
    def _send(self):
        pass
    def read(self):
        client, addr = self.socket.accept()
        self.bot.add_socket(Socket.Socket(client, self.on_read))
        return []
    def parse_data(self, data):
        command = data.split(" ", 1)[0].upper()
        if command == "TRIGGER":
            pass
        else:
            raise ValueError("unknown control socket command: '%s'" %
                command)

    def on_read(self, sock, data):
        data = data.strip("\r\n")
        print(data)
