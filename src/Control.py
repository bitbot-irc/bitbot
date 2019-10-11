import json, os, socket, typing
from src import IRCBot, Logging, PollSource

class ControlClient(object):
    def __init__(self, sock: socket.socket):
        self._socket = sock
        self._read_buffer = b""
        self._write_buffer = b""
        self.version = -1
        self.log_level = None # type: typing.Optional[int]

    def fileno(self) -> int:
        return self._socket.fileno()

    def read_lines(self) -> typing.List[str]:
        try:
            data = self._socket.recv(2048)
        except:
            data = b""
        if not data:
            return None
        lines = (self._read_buffer+data).split(b"\n")
        lines = [line.strip(b"\r") for line in lines]
        self._read_buffer = lines.pop(-1)
        return [line.decode("utf8") for line in lines]

    def write_line(self, line: str):
        self._socket.send(("%s\n" % line).encode("utf8"))

    def disconnect(self):
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except:
            pass
        try:
            self._socket.close()
        except:
            pass


class Control(PollSource.PollSource):
    def __init__(self, bot: IRCBot.Bot, database_location: str):
        self._bot = bot
        self._bot.log.hook(self._on_log)

        self._socket_location = "%s.sock" % database_location
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._clients = {}

    def _on_log(self, levelno: int, line: str):
        for client in self._clients.values():
            if not client.log_level == None and client.log_level <= levelno:
                self._send_action(client, "log", line)

    def bind(self):
        if os.path.exists(self._socket_location):
            os.remove(self._socket_location)
        self._socket.bind(self._socket_location)
        self._socket.listen(1)

    def get_readables(self) -> typing.List[int]:
        return [self._socket.fileno()]+list(self._clients.keys())

    def is_readable(self, fileno: int):
        if fileno == self._socket.fileno():
            client, address = self._socket.accept()
            self._clients[client.fileno()] = ControlClient(client)
            self._bot.log.debug("New control socket connected")
        elif fileno in self._clients:
            client = self._clients[fileno]
            lines = client.read_lines()
            if lines == None:
                client.disconnect()
                del self._clients[fileno]
            else:
                for line in lines:
                    response = self._parse_line(client, line)

    def _parse_line(self, client: ControlClient, line: str):
        id, _, command = line.partition(" ")
        command, _, data = command.partition(" ")
        if not id or not command:
            client.disconnect()
            return

        command = command.lower()
        response_action = "ack"
        response_data = None

        keepalive = True

        if command == "version":
            client.version = int(data)
        elif command == "log":
            client.log_level = Logging.LEVELS[data.lower()]
        elif command == "rehash":
            self._bot.log.info("Reloading config file")
            self._bot.config.load()
            self._bot.log.info("Reloaded config file")
            keepalive = False

        self._send_action(client, response_action, response_data, id)
        if not keepalive:
            client.disconnect()

    def _send_action(self, client: ControlClient, action: str, data: str,
            id: int=None):
        client.write_line(
            json.dumps({"action": action, "data": data, "id": id}))
