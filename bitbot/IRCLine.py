import datetime, typing, uuid
from . import EventManager, IRCObject, utils

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

    def append(self, value: str):
        self._args.append(value)

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

def parse_hostmask(hostmask: str) -> Hostmask:
    nickname, _, username = hostmask.partition("!")
    username, _, hostname = username.partition("@")
    return Hostmask(nickname, username, hostname, hostmask)

MESSAGE_TAG_ESCAPED = [r"\:", r"\s", r"\\", r"\r", r"\n"]
MESSAGE_TAG_UNESCAPED = [";", " ", "\\", "\r", "\n"]
def message_tag_escape(s):
    return utils.irc.multi_replace(s, MESSAGE_TAG_UNESCAPED,
        MESSAGE_TAG_ESCAPED)
def message_tag_unescape(s):
    unescaped = utils.irc.multi_replace(s, MESSAGE_TAG_ESCAPED,
        MESSAGE_TAG_UNESCAPED)
    return unescaped.replace("\\", "")

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
                value_escaped = message_tag_escape(value)
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
        return (line, overflow)
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

def parse_line(line: str) -> ParsedLine:
    tags = {} # type: typing.Dict[str, typing.Any]
    source = None # type: typing.Optional[Hostmask]
    command = None

    if line[0] == "@":
        tags_prefix, line = line[1:].split(" ", 1)

        for tag in filter(None, tags_prefix.split(";")):
            tag, sep, value = tag.partition("=")
            if value:
                tags[tag] = message_tag_unescape(value)
            else:
                tags[tag] = None

    line, trailing_separator, trailing_split = line.partition(" :")

    trailing = None # type: typing.Optional[str]
    if trailing_separator:
        trailing = trailing_split

    if line[0] == ":":
        source_str, line = line[1:].split(" ", 1)
        source = parse_hostmask(source_str)

    command, sep, line = line.partition(" ")
    args = [] # type: typing.List[str]
    if line:
        # this is so that `args` is empty if `line` is empty
        args = line.split(" ")

    if not trailing == None:
        args.append(typing.cast(str, trailing))
    return ParsedLine(command, args, source, tags)

def is_human(line: str):
    return len(line) > 1 and line[0] == "/"
def parse_human(line: str) -> typing.Optional[ParsedLine]:
    command, _, args = line[1:].partition(" ")
    if command == "msg":
        target, _, message = args.partition(" ")
        return ParsedLine("PRIVMSG", [target, message])
    return None

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

class IRCBatch(object):
    def __init__(self, identifier: str, batch_type: str, args: typing.List[str],
            tags: typing.Dict[str, str]=None, source: Hostmask=None):
        self.identifier = identifier
        self.type = batch_type
        self.args = args
        self.tags = tags or {}
        self.source = source
        self._lines = [] # type: typing.List[ParsedLine]
    def add_line(self, line: ParsedLine):
        self._lines.append(line)
    def get_lines(self) -> typing.List[ParsedLine]:
        return self._lines

class IRCSendBatch(IRCBatch):
    def __init__(self, batch_type: str, args: typing.List[str],
            tags: typing.Dict[str, str]=None):
        IRCBatch.__init__(self, str(uuid.uuid4()), batch_type, args, tags)
    def get_lines(self) -> typing.List[ParsedLine]:
        lines = []
        for line in self._lines:
            line.add_tag("batch", self.identifier)
            lines.append(line)

        lines.insert(0, ParsedLine("BATCH",
            ["+%s" % self.identifier, self.type]))
        lines.append(ParsedLine("BATCH", ["-%s" % self.identifier]))
        return lines
