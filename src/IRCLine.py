import datetime, typing
from src import IRCObject, utils

LINE_CUTOFF = 450

class Line(IRCObject.Object):
    def __init__(self, send_time: datetime.datetime, line: str):
        self._line = line
        self.send_time = send_time

        data, truncated = utils.encode_truncate(line, "utf8", LINE_CUTOFF)

        self._data = data
        self._truncated = truncated

        self._on_send = [] # type: typing.List[typing.Callable[[], None]]

    def __repr__(self) -> str:
        return "IRCLine.Line(%s)" % self.__str__()
    def __str__(self) -> str:
        return self._data

    def on_send(self, func: typing.Callable[[], None]):
        self._on_send.append(func)
    def sent(self):
        for func in self._on_send[:]:
            func()

    def data(self) -> bytes:
        return b"%s\r\n" % self._data
