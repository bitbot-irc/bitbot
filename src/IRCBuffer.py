import collections, dataclasses, datetime, re, typing, uuid
from src import IRCBot, IRCServer, utils

MAX_LINES = 64

@dataclasses.dataclass
class BufferLine(object):
    sender: str
    message: str
    action: bool
    tags: dict
    from_self: bool
    method: str

    deleted: bool=False

    notes: typing.Dict[str, str] = dataclasses.field(
        default_factory=dict)

    id: str = dataclasses.field(
        default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime.datetime = dataclasses.field(
        default_factory=utils.datetime.utcnow)

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

    def get(self, index: int=0, from_self=True, deleted=False
            ) -> typing.Optional[BufferLine]:
        for line in self._lines:
            if line.from_self and not from_self:
                continue
            if line.deleted and not deleted:
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

    def find(self, pattern: typing.Union[str, typing.Pattern[str]],
            not_pattern: typing.Union[str, typing.Pattern[str]]=None,
            from_self=True, for_user: str=None, deleted=False
            ) -> typing.Optional[BufferLineMatch]:
        if for_user:
            for_user = self.server.irc_lower(for_user)

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
                    if line.deleted and not deleted:
                        continue
                    return BufferLineMatch(line, match.group(0))
        return None

    def find_id(self, id: str) -> typing.Optional[BufferLine]:
        for line in self._lines:
            if line.id == id:
                return line
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
