import datetime, typing, uuid
from src import IRCObject, utils

# this should be 510 (RFC1459, 512 with \r\n) but a server BitBot uses is broken
LINE_MAX = 470

class IRCArgs(object):
    def __init__(self, args: typing.List[str]):
        self._args = args

    def get(self, index: int) -> typing.Optional[str]:
        if index < 0:
            if len(self._args) > (abs(index)-1):
                return self._args[index]
        elif len(self._args) > index:
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
            source: Hostmask=None,
            tags: typing.Dict[str, str]=None):
        self.id = str(uuid.uuid4())
        self.command = command
        self._args = args
        self.args = IRCArgs(args)
        self.source = source
        self.tags = tags or {} # type: typing.Dict[str, str]
        self._valid = True
        self._assured = False

    def __repr__(self):
        return "ParsedLine(%s)" % self.__str__()
    def __str__(self):
        return self.format()

    def valid(self) -> bool:
        return self._valid
    def invalidate(self):
        self._valid = False

    def assured(self) -> bool:
        return self._assured
    def assure(self):
        self._assured = True

    def add_tag(self, tag: str, value: str=None):
        self.tags[tag] = value or ""
    def has_tag(self, tag: str) -> bool:
        return "tag" in self.tags
    def get_tag(self, tag: str) -> typing.Optional[str]:
        return self.tags[tag]

    def _tag_str(self, tags: typing.Dict[str, str]) -> str:
        tag_pieces = []
        for tag, value in tags.items():
            if value:
                value_escaped = utils.irc.message_tag_escape(value)
                tag_pieces.append("%s=%s" % (tag, value_escaped))
            else:
                tag_pieces.append(tag)

        if tag_pieces:
            return "@%s" % ";".join(tag_pieces)
        return ""

    def _format(self) -> typing.Tuple[str, str]:
        pieces = []
        tags = ""
        if self.tags:
            tags = self._tag_str(self.tags)

        if self.source:
            pieces.append(":%s" % str(self.source))

        pieces.append(self.command.upper())

        if self.args:
            for i, arg in enumerate(self._args):
                if arg and i == len(self._args)-1 and (
                        " " in arg or arg[0] == ":"):
                    pieces.append(":%s" % arg)
                else:
                    pieces.append(arg)

        return tags, " ".join(pieces).replace("\r", "")
    def format(self) -> str:
        tags, line = self._format()
        line, _ = self._newline_truncate(line)
        if tags:
            return "%s %s" % (tags, line)
        else:
            return line

    def _newline_truncate(self, line: str) -> typing.Tuple[str, str]:
        line, sep, overflow = line.partition("\n")
        return [line, overflow]
    def _line_max(self, hostmask: str, margin: int) -> int:
        return LINE_MAX-len((":%s " % hostmask).encode("utf8"))-margin
    def truncate(self, hostmask: str, margin: int=0) -> typing.Tuple[str, str]:
        valid_bytes = b""
        valid_index = -1

        line_max = self._line_max(hostmask, margin)

        tags_formatted, line_formatted = self._format()
        for i, char in enumerate(line_formatted):
            encoded_char = char.encode("utf8")
            if (len(valid_bytes)+len(encoded_char) > line_max
                    or encoded_char == b"\n"):
                break
            else:
                valid_bytes += encoded_char
                valid_index = i
        valid_index += 1

        valid = line_formatted[:valid_index]
        if tags_formatted:
            valid = "%s %s" % (tags_formatted, valid)
        overflow = line_formatted[valid_index:]
        if overflow and overflow[0] == "\n":
            overflow = overflow[1:]

        return valid, overflow

class SentLine(IRCObject.Object):
    def __init__(self, events: "EventManager.Events",
            send_time: datetime.datetime, hostmask: str, line: ParsedLine):
        self.events = events
        self.send_time = send_time
        self._hostmask = hostmask
        self.parsed_line = line

    def __repr__(self) -> str:
        return "IRCLine.SentLine(%s)" % self.__str__()
    def __str__(self) -> str:
        return self._for_wire()

    def _for_wire(self) -> str:
        return self.parsed_line.truncate(self._hostmask)[0]
    def for_wire(self) -> bytes:
        return b"%s\r\n" % self._for_wire().encode("utf8")
