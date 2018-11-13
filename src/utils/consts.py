import typing

BITBOT_HOOKS_MAGIC = "__bitbot_hooks"
BITBOT_EXPORTS_MAGIC = "__bitbot_exports"

class IRCColor(object):
    def __init__(self, irc: int, ansi: typing.List[int]):
        self.irc = irc
        self.ansi = ansi

WHITE =      IRCColor(0,  [1, 37])
BLACK =      IRCColor(1,  [30])
BLUE =       IRCColor(2,  [34])
GREEN =      IRCColor(3,  [32])
RED   =      IRCColor(4,  [1, 31])
BROWN =      IRCColor(5,  [31])
PURPLE =     IRCColor(6,  [35])
ORANGE =     IRCColor(7,  [33])
YELLOW =     IRCColor(8,  [1, 33])
LIGHTGREEN = IRCColor(9,  [1, 32])
CYAN =       IRCColor(10, [36])
LIGHTCYAN =  IRCColor(11, [1, 36])
LIGHTBLUE =  IRCColor(12, [1, 34])
PINK =       IRCColor(13, [1, 35])
GREY =       IRCColor(14, [1, 30])
LIGHTGREY =  IRCColor(15, [37])

BOLD =       "\x02"
ITALIC =     "\x1D"
UNDERLINE =  "\x1F"
INVERT =     "\x16"
COLOR =      "\x03"
RESET =      "\x0F"

