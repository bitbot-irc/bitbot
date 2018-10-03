import string, re

ASCII_UPPER = string.ascii_uppercase
ASCII_LOWER = string.ascii_lowercase
STRICT_RFC1459_UPPER = ASCII_UPPER+r'\[]'
STRICT_RFC1459_LOWER = ASCII_LOWER+r'|{}'
RFC1459_UPPER = STRICT_RFC1459_UPPER+"^"
RFC1459_LOWER = STRICT_RFC1459_LOWER+"~"

def remove_colon(s):
    if s.startswith(":"):
        s = s[1:]
    return s

# case mapping lowercase/uppcase logic
def _multi_replace(s, chars1, chars2):
    for char1, char2 in zip(chars1, chars2):
        s = s.replace(char1, char2)
    return s
def lower(server, s):
    if server.case_mapping == "ascii":
        return _multi_replace(s, ASCII_UPPER, ASCII_LOWER)
    elif server.case_mapping == "rfc1459":
        return _multi_replace(s, RFC1459_UPPER, RFC1459_LOWER)
    elif server.case_mapping == "strict-rfc1459":
        return _multi_replace(s, STRICT_RFC1459_UPPER, STRICT_RFC1459_LOWER)
    else:
        raise ValueError("unknown casemapping '%s'" % server.case_mapping)

# compare a string while respecting case mapping
def equals(server, s1, s2):
    return lower(server, s1) == lower(server, s2)

class IRCHostmask(object):
    def __init__(self, nickname, username, hostname, hostmask):
        self.nickname = nickname
        self.username = username
        self.hostname = hostname
        self.hostmask = hostmask
    def __repr__(self):
        return "IRCHostmask(%s)" % self.__str__()
    def __str__(self):
        return self.hostmask

def seperate_hostmask(hostmask):
    hostmask = remove_colon(hostmask)
    nickname, _, username = hostmask.partition("!")
    username, _, hostname = username.partition("@")
    return IRCHostmask(nickname, username, hostname, hostmask)


class IRCLine(object):
    def __init__(self, tags, prefix, command, args, arbitrary, last, server):
        self.tags = tags
        self.prefix = prefix
        self.command = command
        self.args = args
        self.arbitrary = arbitrary
        self.last = last
        self.server = server

def parse_line(server, line):
    tags = {}
    prefix = None
    command = None

    if line[0] == "@":
        tags_prefix, line = line[1:].split(" ", 1)
        for tag in filter(None, tags_prefix.split(";")):
            tag, _, value = tag.partition("=")
            tags[tag] = value

    line, _, arbitrary = line.partition(" :")
    arbitrary = arbitrary or None

    if line[0] == ":":
        prefix, line = line[1:].split(" ", 1)
        prefix = seperate_hostmask(prefix)
    command, _, line = line.partition(" ")

    args = line.split(" ")
    last = arbitrary or args[-1]

    return IRCLine(tags, prefix, command, args, arbitrary, last, server)

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

def color(s, foreground, background=None):
    foreground = str(foreground).zfill(2)
    if background:
        background = str(background).zfill(2)
    return "%s%s%s%s%s" % (FONT_COLOR, foreground,
        "" if not background else ",%s" % background, s, FONT_COLOR)

def bold(s):
    return "%s%s%s" % (FONT_BOLD, s, FONT_BOLD)

def underline(s):
    return "%s%s%s" % (FONT_UNDERLINE, s, FONT_UNDERLINE)

def strip_font(s):
    s = s.replace(FONT_BOLD, "")
    s = s.replace(FONT_ITALIC, "")
    s = REGEX_COLOR.sub("", s)
    s = s.replace(FONT_COLOR, "")
    return s

