import re
from src import utils

STR_MORE = " (more...)"
STR_MORE_LEN = len(STR_MORE.encode("utf8"))
STR_CONTINUED = "(...continued) "
WORD_BOUNDARY = ' '

class Out(object):
    def __init__(self, server, module_name, target, target_str, tags):
        self.server = server
        self._prefix = self._default_prefix(module_name)
        self._hide_prefix = False
        self.target = target
        self._target_str = target_str
        self._text = ""
        self.written = False
        self._tags = tags
        self._assured = False

    def assure(self):
        self._assured = True

    def write(self, text):
        self._text += text
        self.written = True
        return self
    def writeline(self, line):
        self._text += "%s\n" % line

    def send(self, method):
        if self.has_text():
            prefix = ""
            if not self._hide_prefix:
                prefix = utils.consts.RESET + "[%s] " % self._prefix

            text = self._text[:].replace("\r", "")
            while "\n\n" in text:
                text = text.replace("\n\n", "\n")

            full_text = "%s%s" % (prefix, text)
            line_factory = None
            if method == "PRIVMSG":
                line_factory = utils.irc.protocol.privmsg
            elif method == "NOTICE":
                line_factory = utils.irc.protocol.notice
            else:
                raise ValueError("Unknown command method '%s'" % method)

            line = line_factory(self._target_str, full_text, tags=self._tags)
            if self._assured:
                line.assure()

            valid, truncated = line.truncate(self.server.hostmask(),
                margin=STR_MORE_LEN)

            if truncated:
                valid, truncated = self._adjust_to_word_boundaries(valid, truncated)

                line = utils.irc.parse_line(valid+STR_MORE)
                self._text = "%s%s" % (STR_CONTINUED, truncated)
            else:
                self._text = ""

            sent_line = self.server.send(line)

    def _adjust_to_word_boundaries(self, left, right):
        if right[0] == WORD_BOUNDARY:
            return left, right

        parts = left.rsplit(WORD_BOUNDARY, 1)

        if len(parts) != 2:
            return left, right

        return parts[0], parts[1] + right

    def _default_prefix(self, s: str):
        return s
    def set_prefix(self, prefix):
        self._prefix = self._default_prefix(prefix)
    def append_prefix(self, s: str):
        self._prefix = "%s%s" % (self._prefix, s)
    def hide_prefix(self):
        self._hide_prefix = True

    def has_text(self):
        return bool(self._text)

class StdOut(Out):
    def _default_prefix(self, s: str):
        return utils.irc.color(s, utils.consts.GREEN)
class StdErr(Out):
    def _default_prefix(self, s: str):
        return utils.irc.color(s, utils.consts.RED)

