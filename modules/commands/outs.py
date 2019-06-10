import re
from src import utils

STR_MORE = " (more...)"
STR_CONTINUED = "(...continued) "

class Out(object):
    def __init__(self, server, module_name, target, target_str, tags):
        self.server = server
        self.module_name = module_name
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

    def send(self, method):
        if self.has_text():
            prefix = ""
            if not self._hide_prefix:
                prefix = utils.consts.RESET + "[%s] " % self.prefix()

            full_text = "%s%s" % (prefix, self._text)
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
            sent_line = self.server.send(line)

            if sent_line:
                line.truncate_marker = STR_MORE
                if line.truncated():
                    self._text = "%s%s" % (STR_CONTINUED, line.truncated())
                else:
                    self._text = ""

    def set_prefix(self, prefix):
        self.module_name = prefix
    def hide_prefix(self):
        self._hide_prefix = True

    def has_text(self):
        return bool(self._text)

class StdOut(Out):
    def prefix(self):
        return utils.irc.color(self.module_name, utils.consts.GREEN)
class StdErr(Out):
    def prefix(self):
        return utils.irc.color(self.module_name, utils.consts.RED)

