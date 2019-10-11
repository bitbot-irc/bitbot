import json, os, socket, typing
from src import EventManager, PollSource

class ControlClient(object):
    def __init__(self, sock: socket.socket):
        self._socket = sock
        self._read_buffer = b""
        self._write_buffer = b""

    def fileno(self) -> int:
        return self._socket.fileno()

    def read_lines(self) -> typing.List[str]:
        data = self._socket.recv(2048)
        if not data:
            return []
        lines = (self._read_buffer+data).split(b"\n")
        lines = [line.strip(b"\r") for line in lines]
        self._read_buffer = lines.pop(-1)
        return [line.decode("utf8") for line in lines]

    def write_line(self, line: str):
        self._write_buffer += ("%s\n" % line).encode("utf8")
    def _send(self):
        sent = self._socket.send(self._write_buffer)
        self._write_buffer = self._write_buffer[sent:]
    def writeable(self) -> bool:
        return bool(self._write_buffer)

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
    def __init__(self, events: EventManager.Events, database_location):
        self._socket_location = "%s.sock" % database_location
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._clients = {}

    def bind(self):
        if os.path.exists(self._socket_location):
            os.remove(self._socket_location)
        self._socket.bind(self._socket_location)
        self._socket.listen(1)

    def get_readables(self) -> typing.List[int]:
        return [self._socket.fileno()]+list(self._clients.keys())
    def get_writables(self) -> typing.List[int]:
        return [f for f, c in self._clients.items() if c.writeable()]

    def is_readable(self, fileno: int):
        if fileno == self._socket.fileno():
            client, address = self._socket.accept()
            self._clients[client.fileno()] = ControlClient(client)
        elif fileno in self._clients:
            client = self._clients[fileno]
            lines = client.read_lines()
            if not lines:
                client.disconnect()
                del self._clients[fileno]
            else:
                for line in lines:
                    response = self._parse_line(client, line)
                    client.write_line(response)
    def is_writeable(self, fileno: int):
        self._clients[fileno]._send()

    def _parse_line(self, client: ControlClient, line: str):
        version, _, id = line.partition(" ")
        id, _, data_str = id.partition(" ")
        if version == "0.1":
#            data = json.loads(data_str)
            response = {"action": "ack"}
            return "0.1 %s %s" % (id, json.dumps(response))
