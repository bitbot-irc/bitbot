import json, string, re, typing

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

class IRCHostmask(object):
    def __init__(self, nickname: str, username: str, hostname: str,
            hostmask: str):
        self.nickname = nickname
        self.username = username
        self.hostname = hostname
        self.hostmask = hostmask
    def __repr__(self):
        return "IRCHostmask(%s)" % self.__str__()
    def __str__(self):
        return self.hostmask

def seperate_hostmask(hostmask: str) -> IRCHostmask:
    nickname, _, username = hostmask.partition("!")
    username, _, hostname = username.partition("@")
    return IRCHostmask(nickname, username, hostname, hostmask)

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
    def __getitem__(self, index) -> str:
        return self._args[index]


class IRCLine(object):
    def __init__(self, tags: dict, prefix: typing.Optional[str], command: str,
            args: IRCArgs, has_arbitrary: bool):
        self.tags = tags
        self.prefix = prefix
        self.command = command
        self.args = args
        self.has_arbitrary = has_arbitrary

MESSAGE_TAG_ESCAPED = [r"\:", r"\s", r"\\", r"\r", r"\n"]
MESSAGE_TAG_UNESCAPED = [";", " ", "\\", "\r", "\n"]
def message_tag_escape(s):
    return _multi_replace(s, MESSAGE_TAG_UNESCAPED, MESSAGE_TAG_ESCAPED)
def message_tag_unescape(s):
    return _multi_replace(s, MESSAGE_TAG_ESCAPED, MESSAGE_TAG_UNESCAPED)

def parse_line(line: str) -> IRCLine:
    tags = {}
    prefix = typing.Optional[IRCHostmask]
    command = None

    if line[0] == "@":
        tags_prefix, line = line[1:].split(" ", 1)

        if tags_prefix[0] == "{":
            tags_prefix = message_tag_unescape(tags_prefix)
            tags = json.loads(tags_prefix)
        else:
            for tag in filter(None, tags_prefix.split(";")):
                tag, sep, value = tag.partition("=")
                if sep:
                    tags[tag] = message_tag_unescape(value)
                else:
                    tags[tag] = None

    line, arb_sep, arbitrary_split = line.partition(" :")
    has_arbitrary = bool(arb_sep)
    arbitrary = None # type: typing.Optional[str]
    if has_arbitrary:
        arbitrary = arbitrary_split

    if line[0] == ":":
        prefix_str, line = line[1:].split(" ", 1)
        prefix = seperate_hostmask(prefix_str)

    args = []
    command, sep, line = line.partition(" ")
    if sep:
        args = line.split(" ")

    if arbitrary:
        args.append(arbitrary)

    return IRCLine(tags, prefix, command, IRCArgs(args), has_arbitrary)

COLOR_WHITE, COLOR_BLACK, COLOR_BLUE, COLOR_GREEN = 0, 1, 2, 3
COLOR_RED, COLOR_BROWN, COLOR_PURPLE, COLOR_ORANGE = 4, 5, 6, 7
COLOR_YELLOW, COLOR_LIGHTGREEN, COLOR_CYAN, COLOR_LIGHTCYAN = (8, 9,
    10, 11)
COLOR_LIGHTBLUE, COLOR_PINK, COLOR_GREY, COLOR_LIGHTGREY = (12, 13,
    14, 15)
FONT_BOLD, FONT_ITALIC, FONT_UNDERLINE, FONT_INVERT = ("\x02", "\x1D",
    "\x1F", "\x16")
FONT_COLOR, FONT_RESET = "\x03", "\x0F"
REGEX_COLOR = re.compile("%s\d\d(?:,\d\d)?" % FONT_COLOR)

def color(s: str, foreground: int, background: int=None) -> str:
    foreground = str(foreground).zfill(2)
    if background:
        background = str(background).zfill(2)
    return "%s%s%s%s%s" % (FONT_COLOR, foreground,
        "" if not background else ",%s" % background, s, FONT_COLOR)

def bold(s: str) -> str:
    return "%s%s%s" % (FONT_BOLD, s, FONT_BOLD)

def underline(s: str) -> str:
    return "%s%s%s" % (FONT_UNDERLINE, s, FONT_UNDERLINE)

def strip_font(s: str) -> str:
    s = s.replace(FONT_BOLD, "")
    s = s.replace(FONT_ITALIC, "")
    s = REGEX_COLOR.sub("", s)
    s = s.replace(FONT_COLOR, "")
    return s

OPT_STR = typing.Optional[str]
class IRCConnectionParameters(object):
    def __init__(self, id: int, alias: OPT_STR, hostname: str, port: int,
            password: OPT_STR, tls: bool, ipv4: bool, bindhost: OPT_STR,
            nickname: str, username: OPT_STR, realname: OPT_STR,
            args: typing.Dict[str, str]={}):
        self.id = id
        self.alias = alias
        self.hostname = hostname
        self.port = port
        self.tls = tls
        self.ipv4 = ipv4
        self.bindhost = bindhost
        self.password = password
        self.nickname = nickname
        self.username = username
        self.realname = realname
        self.args = args
