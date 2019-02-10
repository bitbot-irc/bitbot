import datetime, typing
from src import IRCObject, utils

LINE_CUTOFF = 470

class Line(IRCObject.Object):
    def __init__(self, server: "IRCServer.Server", send_time: datetime.datetime,
            line: str):
        self.server = server
        self._line = line
        self.send_time = send_time

        data, truncated = utils.encode_truncate(line, "utf8",
            self._char_limit())

        self._data = data
        self._truncated = truncated

        self._on_send = [] # type: typing.List[typing.Callable[[], None]]

    def __repr__(self) -> str:
        return "IRCLine.Line(%s)" % self.__str__()
    def __str__(self) -> str:
        return self._data

    def _char_limit(self):
        return LINE_CUTOFF-len(":%s " % self.server.hostmask())

    def data(self) -> bytes:
        return b"%s\r\n" % self._data
    def decoded_data(self) -> bytes:
        return self._data.decode("utf8")
    def truncated(self) -> str:
        return self._truncated

    def on_send(self, func: typing.Callable[[], None]):
        self._on_send.append(func)
    def sent(self):
        for func in self._on_send[:]:
            func()

    def end_replace(self, s: str):
        s_encoded = s.encode("utf8")
        s_len = len(s_encoded)

        removed = self._data[-s_len:].decode("utf8")
        self._truncated = removed+self._truncated
        self._data = self._data[:-s_len]+s_encoded
