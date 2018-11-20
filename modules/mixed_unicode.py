import enum
from src import ModuleManager, utils

class Script(enum.Enum):
    Unknown = 0
    Latin = 1
    Cyrillic = 2
    Greek = 3
    Armenian = 4
    FullWidth = 5
    Coptic = 6
WORD_SEPERATORS = [",", " ", "\t", "."]

class Module(ModuleManager.BaseModule):
    def _detect_script(self, char):
        point = ord(char)
        if   0     <= point <= 687:
            return Script.Latin
        elif 880   <= point <= 1023:
            return Script.Greek
        elif 1024  <= point <= 1327:
            return Script.Cyrillic
        elif 1329  <= point <= 1418:
            return Script.Armenian
        elif 65281 <= point <= 65376:
            return Script.FullWidth
        # COPTIC CAPITAL LETTER ALFA .. COPTIC MORPHOLOGICAL DIVIDER
        elif 0x2C80 <= point <= 0x2CFF:
            return Script.Coptic
        return Script.Unknown

    @utils.hook("received.message.channel")
    def channel_message(self, event):
        last_script = None
        last_was_separator = False
        score = 0

        for char in event["message"]:
            if char in WORD_SEPERATORS:
                last_was_separator = True
            else:
                script = self._detect_script(char)
                if not script == Script.Unknown:
                    if last_script and not script == last_script:
                        score += 1
                        if not last_was_separator:
                            score += 1

                    last_script = script

                last_was_separator = False
        self.log.trace("Message given a mixed-unicode score of %d", [score])
