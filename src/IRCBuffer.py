import re, typing
from src import IRCBot, IRCServer, utils

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
        self.lines = []
        self.max_lines = 64
        self._skip_next = False

    def _add_message(self, sender: str, message: str, action: bool, tags: dict,
            from_self: bool, method: str):
        if not self._skip_next:
            line = BufferLine(sender, message, action, tags, from_self, method)
            self.lines.insert(0, line)
            if len(self.lines) > self.max_lines:
                self.lines.pop()
        self._skip_next = False
    def add_message(self, sender: str, message: str, action: bool, tags: dict,
            from_self: bool=False):
        self._add_message(sender, message, action, tags, from_self, "PRIVMSG")
    def add_notice(self, sender: str, message: str, tags: dict,
            from_self: bool=False):
        self._add_message(sender, message, False, tags, from_self, "NOTICE")

    def get(self, index: int=0, **kwargs) -> typing.Optional[BufferLine]:
        from_self = kwargs.get("from_self", True)
        for line in self.lines:
            if line.from_self and not from_self:
                continue
            return line
    def find(self, pattern: typing.Union[str, typing.Pattern[str]], **kwargs
            ) -> typing.Optional[BufferLine]:
        from_self = kwargs.get("from_self", True)
        for_user = kwargs.get("for_user", "")
        for_user = utils.irc.lower(self.server.case_mapping, for_user
            ) if for_user else None
        not_pattern = kwargs.get("not_pattern", None)
        for line in self.lines:
            if line.from_self and not from_self:
                continue
            elif re.search(pattern, line.message):
                if not_pattern and re.search(not_pattern, line.message):
                    continue
                if for_user and not utils.irc.lower(self.server.case_mapping,
                        line.sender) == for_user:
                    continue
                return line
    def skip_next(self):
        self._skip_next = True
