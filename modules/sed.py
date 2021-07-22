#--depends-on commands
#--depends-on config

import re, traceback
from src import ModuleManager, utils

REGEX_SED = re.compile(r"^(?:(\S+)[:,] )?s([/,`#]).*\2")

@utils.export("channelset",
    utils.BoolSetting("sed","Disable/Enable sed in a channel"))
@utils.export("channelset", utils.BoolSetting("sed-sender-only",
    "Disable/Enable sed only looking at the messages sent by the user"))
class Module(ModuleManager.BaseModule):
    def _closest_setting(self, event, setting, default):
        return event["target"].get_setting(setting,
            event["server"].get_setting(setting, default))

    @utils.hook("command.regex")
    @utils.kwarg("command", "sed")
    @utils.kwarg("pattern", REGEX_SED)
    def channel_message(self, event):
        for_user = event["match"].group(1)
        sed_s = event["message"]
        if for_user:
            sed_s = sed_s.split(" ", 1)[1]
        if not self._closest_setting(event, "sed", False):
            return

        try:
            sed = utils.parse.sed.parse(event["message"])
        except:
            traceback.print_exc()
            event["stderr"].write("Invalid regex in pattern")
            return
        sed.replace = utils.irc.bold(sed.replace)

        if self._closest_setting(event, "sed-sender-only", False):
            for_user = event["user"].nickname_lower

        match_line = None
        match_message = None
        with utils.deadline():
            for line in event["target"].buffer.get_all(for_user):
                if not line.from_self:
                    match = sed.match(line.message)
                    if not match == line.message:
                        match_line = line
                        match_message = match
                        break

        if match_line:
            if match_line.action:
                format = "* %s %s"
            else:
                format = "<%s> %s"
            event["stdout"].write(format % (match_line.sender, match_message))
