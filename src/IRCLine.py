import datetime, typing
from src import IRCObject

# this should be 510 (RFC1459, 512 with \r\n) but a server BitBot uses is broken
LINE_CUTOFF = 470

class IRCArgs(object):
    def __init__(self, args: typing.List[str]):
        self._args = args

    def get(self, index: int) -> typing.Optional[str]:
        if len(self._args) > index:
            return self._args[index]
        return None

    def __repr__(self):
        return "IRCArgs(%s)" % self._args
    def __len__(self) -> int:
        return len(self._args)
    def __getitem__(self, index: int) -> str:
        return self._args[index]
    def __setitem__(self, index: int, value: str):
        self._args[index] = value

class Hostmask(object):
    def __init__(self, nickname: str, username: str, hostname: str,
            hostmask: str):
        self.nickname = nickname
        self.username = username
        self.hostname = hostname
        self.hostmask = hostmask
    def __repr__(self):
        return "Hostmask(%s)" % self.__str__()
    def __str__(self):
        return self.hostmask

class ParsedLine(object):
    def __init__(self, command: str, args: typing.List[str],
            prefix: Hostmask=None,
            tags: typing.Dict[str, str]={}):
        self.command = command
        self._args = args
        self.args = IRCArgs(args)
        self.prefix = prefix
        self.tags = {} if tags == None else tags

    def _tag_str(self, tags: typing.Dict[str, str]) -> str:
        tag_str = ""
        for tag, value in tags.items():
            if tag_str:
                tag_str += ","
            tag_str += tag
            if value:
                tag_str += "=%s" % value
        if tag_str:
            tag_str = "@%s" % tag_str
        return tag_str

    def format(self) -> str:
        s = ""
        if self.tags:
            s += "%s " % self._tag_str(self.tags)

        if self.prefix:
            s += "%s " % self.prefix

        s += self.command.upper()

        if self.args:
            if len(self._args) > 1:
                s += " %s" % " ".join(self._args[:-1])

            s += " "
            if " " in self._args[-1] or self._args[-1][0] == ":":
                s += ":%s" % self._args[-1]
            else:
                s += self._args[-1]

        return s

class SentLine(IRCObject.Object):
    def __init__(self, send_time: datetime.datetime, hostmask: str,
            line: ParsedLine):
        self.send_time = send_time
        self._hostmask = hostmask
        self.parsed_line = line

        self._on_send: typing.List[typing.Callable[[], None]] = []
        self.truncate_marker: typing.Optional[str] = None

    def __repr__(self) -> str:
        return "IRCLine.SentLine(%s)" % self.__str__()
    def __str__(self) -> str:
        return self.decoded_data()

    def _char_limit(self) -> int:
        return LINE_CUTOFF-len(":%s " % self._hostmask)

    def _encode_truncate(self) -> typing.Tuple[bytes, str]:
        line = self.parsed_line.format()
        byte_max = self._char_limit()
        encoded = b""
        truncated = ""
        truncate_marker = b""
        if not self.truncate_marker == None:
            truncate_marker = typing.cast(str, self.truncate_marker
                ).encode("utf8")

        for i, character in enumerate(line):
            encoded_character = character.encode("utf8")
            new_len = len(encoded + encoded_character)
            if truncate_marker and (byte_max-new_len) < len(truncate_marker):
                encoded += truncate_marker
                truncated = line[i:]
                break
            elif new_len > byte_max:
                truncated = line[i:]
                break
            else:
                encoded += encoded_character
        return (encoded, truncated)

    def _data(self) -> bytes:
        return self._encode_truncate()[0]
    def data(self) -> bytes:
        return b"%s\r\n" % self._data()
    def decoded_data(self) -> str:
        return self._data().decode("utf8")
    def truncated(self) -> str:
        return self._encode_truncate()[1]

    def on_send(self, func: typing.Callable[[], None]):
        self._on_send.append(func)
    def sent(self):
        for func in self._on_send[:]:
            func()
