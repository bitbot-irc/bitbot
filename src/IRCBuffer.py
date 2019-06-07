import collections, re, typing
from src import IRCBot, IRCServer, utils

MAX_LINES = 64

class BufferLine(object):
    def __init__(self, sender: str, message: str, action: bool, tags: dict,
            from_self: bool, method: str):
        self.sender = sender
        self.message = message
        self.action = action
        self.tags = tags
        self.from_self = from_self
        self.method = method

class Buffer(object):
    def __init__(self, bot: "IRCBot.Bot", server: "IRCServer.Server"):
        self.bot = bot
        self.server = server
        self._lines = collections.deque(maxlen=MAX_LINES
            ) # type: typing.Deque[BufferLine]
        self._skip_next = False

    def _add_message(self, sender: str, message: str, action: bool, tags: dict,
            from_self: bool, method: str):
        if not self._skip_next:
            line = BufferLine(sender, message, action, tags, from_self, method)
            self._lines.appendleft(line)
        self._skip_next = False
    def add_message(self, sender: str, message: str, action: bool, tags: dict,
            from_self: bool=False):
        self._add_message(sender, message, action, tags, from_self, "PRIVMSG")
    def add_notice(self, sender: str, message: str, tags: dict,
            from_self: bool=False):
        self._add_message(sender, message, False, tags, from_self, "NOTICE")

    def get(self, index: int=0, **kwargs) -> typing.Optional[BufferLine]:
        from_self = kwargs.get("from_self", True)
        for line in self._lines:
            if line.from_self and not from_self:
                continue
            return line
        return None
    def find(self, pattern: typing.Union[str, typing.Pattern[str]], **kwargs
            ) -> typing.Optional[BufferLine]:
        from_self = kwargs.get("from_self", True)
        for_user = kwargs.get("for_user", "")
        for_user = self.server.irc_lower(for_user) if for_user else None
        not_pattern = kwargs.get("not_pattern", None)
        for line in self._lines:
            if line.from_self and not from_self:
                continue
            elif re.search(pattern, line.message):
                if not_pattern and re.search(not_pattern, line.message):
                    continue
                if for_user and not self.server.irc_lower(line.sender
                        ) == for_user:
                    continue
                return line
        return None

    def find_from(self, nickname: str) -> typing.Optional[BufferLine]:
        nickname_lower = self.server.irc_lower(nickname)
        for line in self._lines:
            if (not line.from_self
                    and self.server.irc_lower(line.sender) == nickname_lower):
                return line
        return None

    def skip_next(self):
        self._skip_next = True
