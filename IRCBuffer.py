import re
import Utils

class BufferLine(object):
    def __init__(self, sender, message, action, from_self):
        self.sender = sender
        self.message = message
        self.action = action
        self.from_self = from_self

class Buffer(object):
    def __init__(self, bot, server):
        self.bot = bot
        self.server = server
        self.lines = []
        self.max_lines = 64
        self._skip_next = False
    def add_line(self, sender, message, action, from_self=False):
        if not self._skip_next:
            line = BufferLine(sender, message, action, from_self)
            self.lines.insert(0, line)
            if len(self.lines) > self.max_lines:
                self.lines.pop()
        self._skip_next = False
    def get(self, index=0, **kwargs):
        from_self = kwargs.get("from_self", True)
        for line in self.lines:
            if line.from_self and not from_self:
                continue
            return line
    def find(self, pattern, **kwargs):
        from_self = kwargs.get("from_self", True)
        for_user = kwargs.get("for_user", "")
        for_user = Utils.irc_lower(self.server, for_user
            ) if for_user else None
        not_pattern = kwargs.get("not_pattern", None)
        for line in self.lines:
            if line.from_self and not from_self:
                continue
            elif re.search(pattern, line.message):
                if not_pattern and re.search(not_pattern, line.message):
                    continue
                if for_user and not Utils.irc_lower(self.server, line.sender
                        ) == for_user:
                    continue
                return line
    def skip_next(self):
        self._skip_next = True
