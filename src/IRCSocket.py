import datetime, socket, ssl, time, typing
from src import IRCLine, Logging, IRCObject, utils

THROTTLE_LINES = 4
THROTTLE_SECONDS = 1
UNTHROTTLED_MAX_LINES = 10

class Socket(IRCObject.Object):
    def __init__(self, log: Logging.Log, encoding: str, fallback_encoding: str,
            hostname: str, port: int, bindhost: str, tls: bool,
            tls_verify: bool=True, cert: str=None, key: str=None):
        self.log = log

        self._encoding = encoding
        self._fallback_encoding = fallback_encoding
        self._hostname = hostname
        self._port = port
        self._bindhost = bindhost

        self._tls = tls
        self._tls_verify = tls_verify
        self._cert = cert
        self._key = key

        self.connected = False

        self._write_buffer = b""
        self._queued_lines = [] # type: typing.List[IRCLine.SentLine]
        self._buffered_lines = [] # type: typing.List[IRCLine.SentLine]
        self._read_buffer = b""
        self._recent_sends = [] # type: typing.List[float]
        self.cached_fileno = None # type: typing.Optional[int]
        self.bytes_written = 0
        self.bytes_read = 0

        self._write_throttling = False
        self._throttle_when_empty = False

        self.last_read = time.monotonic()
        self.last_send = None # type: typing.Optional[float]

        self.connected_ip = None # type: typing.Optional[str]
        self.conncect_time: float = -1

    def fileno(self) -> int:
        return self.cached_fileno or self._socket.fileno()

    def _tls_wrap(self):
        server_hostname = None
        if not utils.is_ip(self._hostname):
            server_hostname = self._hostname

        self._socket = utils.security.ssl_wrap(self._socket,
            cert=self._cert, key=self._key, verify=self._tls_verify,
            hostname=server_hostname)

    def connect(self):
        bindhost = None
        if self._bindhost:
            bindhost = (self._bindhost, 0)
        self._socket = socket.create_connection((self._hostname, self._port),
            5.0, bindhost)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        if self._tls:
            self._tls_wrap()

        self.connect_time = time.time()
        self.connected_ip = self._socket.getpeername()[0]
        self.cached_fileno = self._socket.fileno()
        self.connected = True

    def disconnect(self):
        self.connected = False
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except:
            pass
        try:
            self._socket.close()
        except:
            pass

    def read(self) -> typing.Optional[typing.List[str]]:
        data = b""
        try:
            data = self._socket.recv(4096)
        except (ConnectionResetError, socket.timeout, OSError):
            self.disconnect()
            return None
        if not data:
            self.disconnect()
            return None
        self.bytes_read += len(data)
        data = self._read_buffer+data
        self._read_buffer = b""

        data_lines = [line.strip(b"\r") for line in data.split(b"\n")]
        if data_lines[-1]:
            self._read_buffer = data_lines[-1]
            self.log.trace("recevied and buffered non-complete line: %s",
                [data_lines[-1]])

        data_lines.pop(-1)
        decoded_lines = []

        for line in data_lines:
            try:
                decoded_line = line.decode(self._encoding)
            except UnicodeDecodeError:
                self.log.trace("can't decode line with '%s', falling back: %s",
                    [self._encoding, line])
                try:
                    decoded_line = line.decode(self._fallback_encoding)
                except UnicodeDecodeError:
                    continue
            decoded_lines.append(decoded_line)

        self.last_read = time.monotonic()
        return decoded_lines

    def send(self, line: IRCLine.SentLine):
        self._queued_lines.append(line)

    def _send(self) -> typing.List[IRCLine.ParsedLine]:
        sent_lines = []
        throttle_space = self.throttle_space()
        if throttle_space:
            to_buffer = self._queued_lines[:throttle_space]
            self._queued_lines = self._queued_lines[throttle_space:]
            for line in to_buffer:
                sent_lines.append(line.parsed_line)

                self._write_buffer += line.data()
                self._buffered_lines.append(line)

        bytes_written_i = self._socket.send(self._write_buffer)
        bytes_written = self._write_buffer[:bytes_written_i]
        lines_sent = bytes_written.count(b"\r\n")
        for i in range(lines_sent):
            self._buffered_lines.pop(0).sent()

        self._write_buffer = self._write_buffer[bytes_written_i:]

        if not self._write_buffer and self._throttle_when_empty:
            self._write_throttling = True

        self.bytes_written += bytes_written_i

        now = time.monotonic()
        self._recent_sends.extend([now]*lines_sent)
        self.last_send = now

        return sent_lines

    def clear_send_buffer(self):
        self._queued_lines.clear()

    def waiting_send(self) -> bool:
        return bool(len(self._write_buffer)) or bool(len(self._queued_lines))
    def waiting_immediate_send(self) -> bool:
        return bool(len(self._write_buffer))

    def throttle_done(self) -> bool:
        return self.send_throttle_timeout() == 0

    def throttle_prune(self):
        now = time.monotonic()
        popped = 0
        for i, recent_send in enumerate(self._recent_sends[:]):
            time_since = now-recent_send
            if time_since >= THROTTLE_SECONDS:
                self._recent_sends.pop(i-popped)
                popped += 1

    def throttle_space(self) -> int:
        if not self._write_throttling:
            return UNTHROTTLED_MAX_LINES
        return max(0, THROTTLE_LINES-len(self._recent_sends))

    def send_throttle_timeout(self) -> float:
        if len(self._write_buffer) or not self._write_throttling:
            return 0

        self.throttle_prune()
        if self.throttle_space() > 0:
            return 0

        time_left = self._recent_sends[0]+THROTTLE_SECONDS
        time_left = time_left-time.monotonic()
        return time_left

    def enable_write_throttle(self):
        self._throttle_when_empty = True
