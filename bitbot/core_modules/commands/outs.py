import re
from bitbot import IRCLine, utils

class StdOut(object):
    def __init__(self, prefix):
        self.prefix = prefix
        self._lines = []
        self._assured = False

    def assure(self):
        self._assured = True

    def write(self, text):
        self.write_lines(
            text.replace("\r", "").replace("\n\n", "\n").split("\n"))
    def write_lines(self, lines):
        self._lines += list(filter(None, lines))

    def get_all(self):
        return self._lines.copy()
    def pop(self):
        return self._lines.pop(0)
    def insert(self, text):
        self._lines.insert(0, text)

    def has_text(self):
        return bool(self._lines)

