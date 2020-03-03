import codecs, datetime, typing, uuid
from src import EventManager, IRCObject, utils

# this should be 510 (RFC1459, 512 with \r\n) but a server BitBot uses is broken
LINE_MAX = 510

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
        if tags:
            return "%s %s" % (tags, line)
        else:
            return line

class SendableLine(ParsedLine):
    def __init__(self, command: str, args: typing.List[str],
            margin: int=0, tags: typing.Dict[str, str]=None):
        ParsedLine.__init__(self, command, args, None, tags)
        self._margin = margin

    def push_last(self, arg: str, extra_margin: int=0,
            human_trunc: bool=False) -> typing.Optional[str]:
        last_arg = self.args[-1]
        tags, line = self._format()
        n = len(line.encode("utf8")) # get length of current line
        n += self._margin            # margin used for :hostmask
        n += 1                       # +1 for space on new arg
        if " " in arg and not " " in last_arg:
            n += 1                   # +1 for colon on new arg
        n += extra_margin            # used for things like (more ...)

        overflow: typing.Optional[str] = None

        if (n+len(arg.encode("utf8"))) > LINE_MAX:
            for i, char in enumerate(codecs.iterencode(arg, "utf8")):
                n += len(char)
                if n > LINE_MAX:
                    arg, overflow = arg[:i], arg[i:]
                    if human_trunc and not overflow[0] == " ":
                        new_arg, sep, new_overflow = arg.rpartition(" ")
                        if sep:
                            arg = new_arg
                            overflow = new_overflow+overflow
                    break
        if arg:
            self.args[-1] = last_arg+arg
        return overflow

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
        return str(self.parsed_line)
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
