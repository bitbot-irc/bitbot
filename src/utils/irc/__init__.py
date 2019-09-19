import json, string, re, typing, uuid
from src import IRCLine, utils
from . import protocol

ASCII_UPPER = string.ascii_uppercase
ASCII_LOWER = string.ascii_lowercase
STRICT_RFC1459_UPPER = ASCII_UPPER+r'\[]'
STRICT_RFC1459_LOWER = ASCII_LOWER+r'|{}'
RFC1459_UPPER = STRICT_RFC1459_UPPER+"^"
RFC1459_LOWER = STRICT_RFC1459_LOWER+"~"

# case mapping lowercase/uppcase logic
def _multi_replace(s: str,
        chars1: typing.Iterable[str],
        chars2: typing.Iterable[str]) -> str:
    for char1, char2 in zip(chars1, chars2):
        s = s.replace(char1, char2)
    return s
def lower(case_mapping: str, s: str) -> str:
    if case_mapping == "ascii":
        return _multi_replace(s, ASCII_UPPER, ASCII_LOWER)
    elif case_mapping == "rfc1459":
        return _multi_replace(s, RFC1459_UPPER, RFC1459_LOWER)
    elif case_mapping == "strict-rfc1459":
        return _multi_replace(s, STRICT_RFC1459_UPPER, STRICT_RFC1459_LOWER)
    else:
        raise ValueError("unknown casemapping '%s'" % case_mapping)

# compare a string while respecting case mapping
def equals(case_mapping: str, s1: str, s2: str) -> bool:
    return lower(case_mapping, s1) == lower(case_mapping, s2)

def parse_hostmask(hostmask: str) -> IRCLine.Hostmask:
    nickname, _, username = hostmask.partition("!")
    username, _, hostname = username.partition("@")
    return IRCLine.Hostmask(nickname, username, hostname, hostmask)

MESSAGE_TAG_ESCAPED = [r"\:", r"\s", r"\\", r"\r", r"\n"]
MESSAGE_TAG_UNESCAPED = [";", " ", "\\", "\r", "\n"]
def message_tag_escape(s):
    return _multi_replace(s, MESSAGE_TAG_UNESCAPED, MESSAGE_TAG_ESCAPED)
def message_tag_unescape(s):
    unescaped = _multi_replace(s, MESSAGE_TAG_ESCAPED, MESSAGE_TAG_UNESCAPED)
    return unescaped.replace("\\", "")

def parse_line(line: str) -> IRCLine.ParsedLine:
    tags = {} # type: typing.Dict[str, typing.Any]
    source = None # type: typing.Optional[IRCLine.Hostmask]
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

    return IRCLine.ParsedLine(command, args, source, tags)

REGEX_COLOR = re.compile("%s(?:(\d{1,2})(?:,(\d{1,2}))?)?" % utils.consts.COLOR)

def color(s: str, foreground: utils.consts.IRCColor,
        background: utils.consts.IRCColor=None) -> str:
    foreground_s = str(foreground.irc).zfill(2)
    background_s = ""
    if background:
        background_s = ",%s" % str(background.irc).zfill(2)

    return "%s%s%s%s%s" % (utils.consts.COLOR, foreground_s, background_s, s,
        utils.consts.COLOR)

def bold(s: str) -> str:
    return "%s%s%s" % (utils.consts.BOLD, s, utils.consts.BOLD)

def underline(s: str) -> str:
    return "%s%s%s" % (utils.consts.UNDERLINE, s, utils.consts.UNDERLINE)

def strip_font(s: str) -> str:
    s = s.replace(utils.consts.BOLD, "")
    s = s.replace(utils.consts.ITALIC, "")
    s = REGEX_COLOR.sub("", s)
    s = s.replace(utils.consts.COLOR, "")
    return s

FORMAT_TOKENS = [
    utils.consts.BOLD,
    utils.consts.RESET,
    utils.consts.UNDERLINE
]
FORMAT_STRIP = [
    "\x08" # backspace
]
def _format_tokens(s: str) -> typing.List[str]:
    is_color = False
    foreground = ""
    background = ""
    is_background = False
    matches = [] # type: typing.List[str]

    for i, char in enumerate(s):
        last_char = i == len(s)-1
        if is_color:
            can_add = False
            current_color = background if is_background else foreground
            color_finished = False
            if char.isdigit() and len(current_color) < 2:
                if is_background:
                    background += char
                else:
                    foreground += char
                color_finished = (len(current_color)+1) == 2

            if char == "," and not is_background:
                is_background = True
            elif not char.isdigit() or (color_finished and last_char):
                color = foreground
                if background:
                    color += ","+background

                matches.append("\x03%s" % color)
                is_color = False
                foreground = ""
                background = ""
                is_background = False

        if char == utils.consts.COLOR:
            if is_color:
                matches.append(char)
            else:
                is_color = True
        elif char in FORMAT_TOKENS:
            matches.append(char)
        elif char in FORMAT_STRIP:
            matches.append(char)
    return matches

def _color_match(code: typing.Optional[str], foreground: bool) -> str:
    if not code:
        return ""
    color = utils.consts.COLOR_CODES[int(code)]
    return color.to_ansi(not foreground)

def parse_format(s: str) -> str:
    has_foreground = False
    has_background = False
    bold = False
    underline = False

    for token in _format_tokens(s):
        replace = ""
        type = token[0]

        if type == utils.consts.COLOR:
            match = REGEX_COLOR.match(token)

            if match and (match.group(1) or match.group(2)):
                foreground = _color_match(match.group(1), True)
                background = _color_match(match.group(2), False)

                if foreground:
                    replace += foreground
                    has_foreground = True
                if background:
                    replace += background
                    has_background = True
            else:
                if has_foreground:
                    has_foreground = False
                    replace += utils.consts.ANSI_FOREGROUND_RESET
                if has_background:
                    has_background = False
                    replace += utils.consts.ANSI_BACKGROUND_RESET
        elif type == utils.consts.BOLD:
            if bold:
                replace += utils.consts.ANSI_BOLD_RESET
            else:
                replace += utils.consts.ANSI_BOLD
            bold = not bold
        elif type == utils.consts.RESET:
            replace += utils.consts.ANSI_RESET
        elif type == utils.consts.UNDERLINE:
            if underline:
                replace += utils.consts.ANSI_UNDERLINE_RESET
            else:
                replace += utils.consts.ANSI_UNDERLINE
            underline = not underline
        elif type in FORMAT_STRIP:
            replace = ""

        s = s.replace(token, replace, 1)

    if has_foreground:
        s += utils.consts.ANSI_FOREGROUND_RESET
    if has_background:
        s += utils.consts.ANSI_BACKGROUND_RESET
    if bold:
        s += utils.consts.ANSI_BOLD_RESET
    if underline:
        s += utils.consts.ANSI_UNDERLINE_RESET

    return s

OPT_STR = typing.Optional[str]
class IRCConnectionParameters(object):
    def __init__(self, id: int, alias: str, hostname: str, port: int,
            password: OPT_STR, tls: bool, bindhost: OPT_STR, nickname: str,
            username: OPT_STR, realname: OPT_STR,
            args: typing.Dict[str, str]={}):
        self.id = id
        self.alias = alias
        self.hostname = hostname
        self.port = port
        self.tls = tls
        self.bindhost = bindhost
        self.password = password
        self.nickname = nickname
        self.username = username
        self.realname = realname
        self.args = args

class CTCPMessage(object):
    def __init__(self, command: str, message: str):
        self.command = command
        self.message = message
def parse_ctcp(s: str) -> typing.Optional[CTCPMessage]:
    ctcp = s.startswith("\x01")
    if s.startswith("\x01"):
        ctcp_command, sep, ctcp_message = s[1:].partition(" ")
        if ctcp_command.endswith("\x01"):
            ctcp_command = ctcp_command[:-1]
        if ctcp_message.endswith("\x01"):
            ctcp_message = ctcp_message[:-1]
        return CTCPMessage(ctcp_command, ctcp_message)

    return None

class IRCBatch(object):
    def __init__(self, identifier: str, batch_type: str, args: typing.List[str],
            tags: typing.Dict[str, str]=None, source: IRCLine.Hostmask=None):
        self.identifier = identifier
        self.type = batch_type
        self.args = args
        self.tags = tags or {}
        self.source = source
        self._lines = [] # type: typing.List[IRCLine.ParsedLine]
    def add_line(self, line: IRCLine.ParsedLine):
        self._lines.append(line)
    def get_lines(self) -> typing.List[IRCLine.ParsedLine]:
        return self._lines

class IRCSendBatch(IRCBatch):
    def __init__(self, batch_type: str, args: typing.List[str],
            tags: typing.Dict[str, str]=None):
        IRCBatch.__init__(self, str(uuid.uuid4()), batch_type, args, tags)
    def get_lines(self) -> typing.List[IRCLine.ParsedLine]:
        lines = []
        for line in self._lines:
            line.add_tag("batch", self.identifier)
            lines.append(line)

        lines.insert(0, IRCLine.ParsedLine("BATCH",
            ["+%s" % self.identifier, self.type]))
        lines.append(IRCLine.ParsedLine("BATCH", ["-%s" % self.identifier]))
        return lines

class Capability(object):
    def __init__(self, ratified_name: typing.Optional[str],
            draft_name: str=None, alias: str=None,
            depends_on: typing.List[str]=None):
        self.alias = alias or ratified_name
        self._caps = set([ratified_name, draft_name])
        self.depends_on = depends_on or []
        self._on_ack_callbacks = [
            ] # type: typing.List[typing.Callable[[], None]]

    def available(self, capabilities: typing.Iterable[str]
            ) -> typing.Optional[str]:
        match = list(set(capabilities)&self._caps)
        return match[0] if match else None

    def match(self, capability: str) -> typing.Optional[str]:
        cap = list(set([capability])&self._caps)
        return cap[0] if cap else None

    def copy(self):
        return Capability(*self._caps, alias=self.alias,
            depends_on=self.depends_on[:])

    def on_ack(self, callback: typing.Callable[[], None]):
        self._on_ack_callbacks.append(callback)
    def ack(self):
        for callback in self._on_ack_callbacks:
            callback()
    def nak(self):
        pass

class MessageTag(object):
    def __init__(self, name: typing.Optional[str], draft_name: str=None):
        self._names = set([name, draft_name])
    def get_value(self, tags: typing.Dict[str, str]) -> typing.Optional[str]:
        key = list(set(tags.keys())&self._names)
        return tags[key[0]] if key else None
    def present(self, tags: typing.Dict[str, str]) -> bool:
        return bool(set(tags.keys())&self._names)
    def match(self, tag: str) -> typing.Optional[str]:
        key = list(set([tag])&self._names)
        return key[0] if key else None

class BatchType(object):
    def __init__(self, name: typing.Optional[str], draft_name: str=None):
        self._names = set([name, draft_name])
    def match(self, type: str) -> typing.Optional[str]:
        t = list(set([type])&self._names)
        return t[0] if t else None

def hostmask_match_many(hostmasks: typing.List[str], pattern: str
        ) -> typing.Optional[str]:
    part1_out = []
    for part1 in pattern.split("?"):
        part2_out = []
        for part2 in part1.split("*"):
            part2_out.append(re.escape(part2))
        part1_out.append(".*".join(part2_out))
    pattern_re = re.compile(".".join(part1_out))
    for hostmask in hostmasks:
        if pattern_re.match(hostmask):
            return hostmask
    return None

def hostmask_match(hostmask: str, pattern: str) -> bool:
    return not hostmask_match_many([hostmask], pattern) == None
