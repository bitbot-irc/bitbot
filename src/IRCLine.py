import datetime, typing
from src import IRCObject

class Line(IRCObject.Object):
    def __init__(self, send_time: datetime.datetime, data: bytes):
        self.send_time = send_time
        self.data = data

        self._on_send = [] # type: typing.List[typing.Callable[[], None]]

    def __repr__(self) -> str:
        return "IRCLine.Line(%s)" % self.__str__()
    def __str__(self) -> str:
        return self.data

    def on_send(self, func: typing.Callable[[], None]):
        self._on_send.append(func)
    def sent(self):
        for func in self._on_send[:]:
            func()
