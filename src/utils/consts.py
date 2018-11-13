import typing

BITBOT_HOOKS_MAGIC = "__bitbot_hooks"
BITBOT_EXPORTS_MAGIC = "__bitbot_exports"

class IRCColor(object):
    def __init__(self, irc: int, ansi: int, ansi_bold: bool):
        self.irc = irc
        self.ansi = ansi
        self.ansi_bold = ansi_bold

COLOR_NAMES = {}
COLOR_CODES = {}
def _color(name: str, irc: int, ansi: int, ansi_bold: bool):
    color = IRCColor(irc, ansi, ansi_bold)
    COLOR_NAMES[name] = color
    COLOR_CODES[irc] = color
    return color

WHITE      = _color("white",       0,  37, True)
BLACK      = _color("black",       1,  30, False)
BLUE       = _color("blue",        2,  34, False)
GREEN      = _color("green",       3,  32, False)
RED        = _color("red",         4,  31, True)
BROWN      = _color("brown",       5,  31, False)
PURPLE     = _color("purple",      6,  35, False)
ORANGE     = _color("orange",      7,  33, False)
YELLOW     = _color("yellow",      8,  33, True)
LIGHTGREEN = _color("light green", 9,  32, True)
CYAN       = _color("cyan",        10, 36, False)
LIGHTCYAN  = _color("light cyan",  11, 36, True)
LIGHTBLUE  = _color("light blue",  12, 34, True)
PINK       = _color("pink",        13, 35, True)
GREY       = _color("grey",        14, 30, True)
LIGHTGREY  = _color("light grey",  15, 37, False)

BOLD      = "\x02"
ITALIC    = "\x1D"
UNDERLINE = "\x1F"
INVERT    = "\x16"
COLOR     = "\x03"
RESET     = "\x0F"

ANSI_FORMAT      = "\033[%sm"
ANSI_RESET       = "\033[0m"
ANSI_COLOR_RESET = "\033[22m"
ANSI_BOLD        = "\033[1m"
ANSI_BOLD_RESET  = "\033[21m"
