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
            if method == "PRIVMSG":
                line = self.server.send_message(self._target_str, full_text,
                    tags=self._tags)
            elif method == "NOTICE":
                line = self.server.send_notice(self._target_str, full_text,
                    tags=self._tags)
            else:
                raise ValueError("Unknown command method '%s'" % method)

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

