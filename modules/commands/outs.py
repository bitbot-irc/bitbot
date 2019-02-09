import re
from src import utils

OUT_CUTOFF = 400
REGEX_CUTOFF = re.compile(r"^.{1,%d}(?:\s|$)" % OUT_CUTOFF)

STR_MORE = "%s (more...)" % utils.consts.RESET
STR_CONTINUED = "(...continued) "

class Out(object):
    def __init__(self, server, module_name, target, msgid, statusmsg):
        self.server = server
        self.module_name = module_name
        self._hide_prefix = False
        self.target = target
        self._text = ""
        self.written = False
        self._msgid = msgid
        self._statusmsg = statusmsg

    def write(self, text):
        self._text += text
        self.written = True
        return self

    def send(self, method):
        if self.has_text():
            text = self._text
            text_encoded = text.encode("utf8")
            if len(text_encoded) > OUT_CUTOFF:
                text = "%s%s" % (text_encoded[:OUT_CUTOFF].decode("utf8"
                    ).rstrip(), STR_MORE)
                self._text = "%s%s" % (STR_CONTINUED, text_encoded[OUT_CUTOFF:
                    ].decode("utf8").lstrip())
            else:
                self._text = ""


            tags = {}
            if self._msgid:
                tags["+draft/reply"] = self._msgid

            prefix = ""
            if not self._hide_prefix:
                prefix = utils.consts.RESET + "[%s] " % self.prefix()

            target_str = "%s%s" % (self._statusmsg, self.target.name)
            full_text = "%s%s" % (prefix, text)
            if method == "PRIVMSG":
                self.server.send_message(target_str, full_text, tags=tags)
            elif method == "NOTICE":
                self.server.send_notice(target_str, full_text, tags=tags)

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
        return utils.irc.color("!"+self.module_name, utils.consts.RED)

