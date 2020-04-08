import dataclasses, json, string, re, typing, uuid
from . import consts

ASCII_UPPER = string.ascii_uppercase
ASCII_LOWER = string.ascii_lowercase
STRICT_RFC1459_UPPER = ASCII_UPPER+r'\[]'
STRICT_RFC1459_LOWER = ASCII_LOWER+r'|{}'
RFC1459_UPPER = STRICT_RFC1459_UPPER+"^"
RFC1459_LOWER = STRICT_RFC1459_LOWER+"~"

# case mapping lowercase/uppcase logic
def multi_replace(s: str,
        chars1: typing.Iterable[str],
        chars2: typing.Iterable[str]) -> str:
    for char1, char2 in zip(chars1, chars2):
        s = s.replace(char1, char2)
    return s
def lower(case_mapping: str, s: str) -> str:
    if case_mapping == "ascii":
        return multi_replace(s, ASCII_UPPER, ASCII_LOWER)
    elif case_mapping == "rfc1459":
        return multi_replace(s, RFC1459_UPPER, RFC1459_LOWER)
    elif case_mapping == "strict-rfc1459":
        return multi_replace(s, STRICT_RFC1459_UPPER, STRICT_RFC1459_LOWER)
    else:
        raise ValueError("unknown casemapping '%s'" % case_mapping)

# compare a string while respecting case mapping
def equals(case_mapping: str, s1: str, s2: str) -> bool:
    return lower(case_mapping, s1) == lower(case_mapping, s2)

REGEX_COLOR = re.compile("%s(?:(\d{1,2})(?:,(\d{1,2}))?)?" % consts.COLOR)

def color(s: str, foreground: consts.IRCColor,
        background: consts.IRCColor=None,
        terminate: bool=True) -> str:
    foreground_s = str(foreground.irc).zfill(2)
    background_s = ""
    if background:
        background_s = ",%s" % str(background.irc).zfill(2)

    out = f"{consts.COLOR}{foreground_s}{background_s}{s}"
    if terminate:
        out += consts.COLOR

    return out

HASH_STOP = ["_", "|", "["]
HASH_COLORS = [consts.CYAN, consts.PURPLE, consts.GREEN, consts.ORANGE,
    consts.LIGHTBLUE, consts.TRANSPARENT, consts.LIGHTCYAN, consts.PINK,
    consts.LIGHTGREEN, consts.BLUE]
def hash_colorize(s: str):
    hash = 5381
    non_stop = False
    for i, char in enumerate(s):
        if not char in HASH_STOP:
            non_stop = True
        elif non_stop:
            break
        hash ^= ((hash<<5)+(hash>>2)+ord(char))&0xFFFFFFFFFFFFFFFF

    return color(s, HASH_COLORS[hash%len(HASH_COLORS)])

def bold(s: str) -> str:
    return f"{consts.BOLD}{s}{consts.BOLD}"

def underline(s: str) -> str:
    return f"{consts.UNDERLINE}{s}{consts.UNDERLINE}"

FORMAT_TOKENS = [
    consts.BOLD,
    consts.RESET,
    consts.UNDERLINE
]
FORMAT_STRIP = [
    "\x08" # backspace
]

def _format_tokens(s: str) -> typing.List[str]:
    tokens: typing.List[str] = []

    s_copy = list(s)
    while s_copy:
        token = s_copy.pop(0)
        if token == "\x03":
            for i in range(2):
                if s_copy and s_copy[0].isdigit():
                    token += s_copy.pop(0)
            if (len(s_copy) > 1 and
                    s_copy[0] == "," and
                    s_copy[1].isdigit()):
                token += s_copy.pop(0)
                token += s_copy.pop(0)
                if s_copy and s_copy[0].isdigit():
                    token += s_copy.pop(0)

            tokens.append(token)
        elif (token in FORMAT_TOKENS or
                token in FORMAT_STRIP):
            tokens.append(token)
    return tokens

def _color_match(code: typing.Optional[str], foreground: bool) -> str:
    if not code:
        return ""
    color = consts.COLOR_CODES[int(code)]
    return color.to_ansi(not foreground)

def parse_format(s: str) -> str:
    has_foreground = False
    has_background = False
    bold = False
    underline = False

    for token in _format_tokens(s):
        replace = ""
        type = token[0]

        if type == consts.COLOR:
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
                    replace += consts.ANSI_FOREGROUND_RESET
                if has_background:
                    has_background = False
                    replace += consts.ANSI_BACKGROUND_RESET
        elif type == consts.BOLD:
            if bold:
                replace += consts.ANSI_BOLD_RESET
            else:
                replace += consts.ANSI_BOLD
            bold = not bold
        elif type == consts.RESET:
            replace += consts.ANSI_RESET
        elif type == consts.UNDERLINE:
            if underline:
                replace += consts.ANSI_UNDERLINE_RESET
            else:
                replace += consts.ANSI_UNDERLINE
            underline = not underline
        elif type in FORMAT_STRIP:
            replace = ""

        s = s.replace(token, replace, 1)

    s += consts.ANSI_RESET
    return s

def strip_font(s: str) -> str:
    for token in _format_tokens(s):
        s = s.replace(token, "", 1)
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

@dataclasses.dataclass
class HostmaskPattern(object):
    original: str
    pattern: typing.Pattern

    def match(self, hostmask: str):
        return bool(self.pattern.fullmatch(hostmask))
def hostmask_parse(hostmask: str):
    part1_out = []
    for part1 in hostmask.split("?"):
        part2_out = []
        for part2 in part1.split("*"):
            part2_out.append(re.escape(part2))
        part1_out.append(".*".join(part2_out))
    return HostmaskPattern(hostmask, re.compile(".".join(part1_out)))

def hostmask_match_many(hostmasks: typing.List[str], pattern: HostmaskPattern,
        ) -> typing.Generator[str, None, None]:
    for hostmask in hostmasks:
        if pattern.match(hostmask):
            yield hostmask
    return None

def hostmask_match(hostmask: str, pattern: HostmaskPattern) -> bool:
    return any(hostmask_match_many([hostmask], pattern))
