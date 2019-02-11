import datetime, socket, ssl, time, typing
from src import IRCLine, Logging, IRCObject, utils

THROTTLE_LINES = 4
THROTTLE_SECONDS = 1
UNTHROTTLED_MAX_LINES = 10

class Socket(IRCObject.Object):
    def __init__(self, log: Logging.Log, encoding: str, fallback_encoding: str,
            hostname: str, port: int, ipv4: bool, bindhost: str, tls: bool,
            tls_verify: bool=True, cert: str=None, key: str=None):
        self.log = log

        self._encoding = encoding
        self._fallback_encoding = fallback_encoding
        self._hostname = hostname
        self._port = port
        self._ipv4 = ipv4
        self._bindhost = bindhost

        self._tls = tls
        self._tls_verify = tls_verify
        self._cert = cert
        self._key = key

        self.connected = False

        self._write_buffer = b""
        self._queued_lines = [] # type: typing.List[IRCLine.Line]
        self._buffered_lines = [] # type: typing.List[IRCLine.Line]
        self._write_throttling = False
        self._read_buffer = b""
        self._recent_sends = [] # type: typing.List[float]
        self.cached_fileno = None # type: typing.Optional[int]
        self.bytes_written = 0
        self.bytes_read = 0

        self.last_read = time.monotonic()
        self.last_send = None # type: typing.Optional[float]

        self.connected_ip = None

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
        family = socket.AF_INET if self._ipv4 else socket.AF_INET6
        self._socket = socket.socket(family, socket.SOCK_STREAM)

        self._socket.settimeout(5.0)

        if self._bindhost:
            self._socket.bind((self._bindhost, 0))
        if self._tls:
            self._tls_wrap()

        self._socket.connect((self._hostname, self._port))
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
            except:
                self.log.trace("can't decode line with '%s', falling back",
                    [self._encoding])
                try:
                    decoded_line = line.decode(self._fallback_encoding)
                except:
                    continue
            decoded_lines.append(decoded_line)

        self.last_read = time.monotonic()
        self.ping_sent = False
        return decoded_lines

    def send(self, line: IRCLine.Line):
        self._queued_lines.append(line)

    def _send(self) -> typing.List[str]:
        decoded_sent = []
        if not len(self._write_buffer):
            throttle_space = self.throttle_space()
            to_buffer = self._queued_lines[:throttle_space]
            self._queued_lines = self._queued_lines[throttle_space:]
            for line in to_buffer:
                decoded_data = line.decoded_data()
                decoded_sent.append(decoded_data)

                self._write_buffer += line.data()
                self._buffered_lines.append(line)

        bytes_written_i = self._socket.send(self._write_buffer)
        bytes_written = self._write_buffer[:bytes_written_i]
        lines_sent = bytes_written.count(b"\r\n")
        for i in range(lines_sent):
            self._buffered_lines.pop(0).sent()

        self._write_buffer = self._write_buffer[bytes_written_i:]

        self.bytes_written += bytes_written_i

        now = time.monotonic()
        self._recent_sends.append(now)
        self.last_send = now

        return decoded_sent

    def waiting_send(self) -> bool:
        return bool(len(self._write_buffer)) or bool(len(self._queued_lines))

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

    def set_write_throttling(self, is_on: bool):
        self._write_throttling = is_on
