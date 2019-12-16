import collections, dataclasses, re, typing
from . import IRCBot, IRCServer, utils

MAX_LINES = 64

@dataclasses.dataclass
class BufferLine(object):
    sender: str
    message: str
    action: bool
    tags: dict
    from_self: bool
    method: str
    notes: typing.Dict[str, str] = dataclasses.field(
        default_factory=dict)

class BufferLineMatch(object):
    def __init__(self, line: BufferLine, match: str):
        self.line = line
        self.match = match

class Buffer(object):
    def __init__(self, bot: "IRCBot.Bot", server: "IRCServer.Server"):
        self.bot = bot
        self.server = server
        self._lines = collections.deque(maxlen=MAX_LINES
            ) # type: typing.Deque[BufferLine]

    def add(self, line: BufferLine):
        self._lines.appendleft(line)

    def get(self, index: int=0, **kwargs) -> typing.Optional[BufferLine]:
        from_self = kwargs.get("from_self", True)
        for line in self._lines:
            if line.from_self and not from_self:
                continue
            return line
        return None
    def get_all(self, for_user: typing.Optional[str]=None):
        if not for_user == None:
            for line in self._lines:
                if self.server.irc_lower(line.sender) == for_user:
                    yield line
        else:
            for line in self._lines:
                yield line
    def find(self, pattern: typing.Union[str, typing.Pattern[str]], **kwargs
            ) -> typing.Optional[BufferLineMatch]:
        from_self = kwargs.get("from_self", True)
        for_user = kwargs.get("for_user", "")
        for_user = self.server.irc_lower(for_user) if for_user else None
        not_pattern = kwargs.get("not_pattern", None)
        for line in self._lines:
            if line.from_self and not from_self:
                continue
            else:
                match = re.search(pattern, line.message)
                if match:
                    if not_pattern and re.search(not_pattern, line.message):
                        continue
                    if for_user and not self.server.irc_lower(line.sender
                            ) == for_user:
                        continue
                    return BufferLineMatch(line, match.group(0))
        return None

    def find_from(self, nickname: str) -> typing.Optional[BufferLine]:
        lines = self.find_many_from(nickname, 1)
        if lines:
            return lines[0]
        else:
            return None
    def find_many_from(self, nickname: str, max: int
            ) -> typing.List[BufferLine]:
        nickname_lower = self.server.irc_lower(nickname)
        found_lines = []
        for line in self._lines:
            if (not line.from_self
                    and self.server.irc_lower(line.sender) == nickname_lower):
                found_lines.append(line)
                if len(found_lines) == max:
                    break
        return found_lines
