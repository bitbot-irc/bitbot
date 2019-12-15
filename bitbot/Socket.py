import socket, typing

class Socket(object):
    def __init__(self, socket: socket.socket,
            on_read: typing.Callable[["Socket", str], None],
            encoding: str="utf8"):
        self.socket = socket
        self._on_read = on_read
        self.encoding = encoding

        self._write_buffer = b""
        self._read_buffer = b""
        self.delimiter = None
        self.length = None
        self.connected = True

    def fileno(self) -> int:
        return self.socket.fileno()

    def disconnect(self):
        self.connected = False

    def _decode(self, s: bytes) -> str:
        return s.decode(self.encoding)
    def _encode(self, s: str) -> bytes:
        return s.encode(self.encoding)

    def read(self) -> typing.Optional[typing.List[str]]:
        data = self.socket.recv(1024)
        if not data:
            return None

        data = self._read_buffer+data
        self._read_buffer = b""
        if not self.delimiter == None:
            data_split = data.split(self.delimiter)
            if data_split[-1]:
                self._read_buffer = data_split.pop(-1)
            return [self._decode(data) for data in data_split]
        return [self._decode(data)]

    def parse_data(self, data: str):
        self._on_read(self, data)

    def send(self, data: str):
        self._write_buffer += self._encode(data)

    def _send(self):
        self._write_buffer = self._write_buffer[self.socket.send(
            self._write_buffer):]

    def waiting_send(self) -> bool:
        return bool(len(self._write_buffer))
