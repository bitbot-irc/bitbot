#--depends-on commands
#--depends-on config

import re, traceback
from src import ModuleManager, utils

REGEX_SPLIT = re.compile("(?<!\\\\)/")
REGEX_SED = re.compile("^(?:(\\S+)[:,] )?s/")
SED_AMPERSAND = re.compile(r"((?:^|[^\\])(?:\\\\)*)&")

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
        sed_split = re.split(REGEX_SPLIT, event["message"], 3)
        if len(sed_split) > 2:
            if not self._closest_setting(event, "sed", False):
                return

            regex_flags = 0
            flags = (sed_split[3:] or [""])[0]
            count = None

            last_flag = ""
            for flag in flags:
                if flag.isdigit():
                    if last_flag.isdigit():
                        count = int(str(count) + flag)
                    elif not count:
                        count = int(flag)
                elif flag == "i":
                    regex_flags |= re.I
                elif flag == "g":
                    count = 0
                last_flag = flag
            if count == None:
                count = 1

            try:
                pattern = re.compile(sed_split[1], regex_flags)
            except:
                traceback.print_exc()
                event["stderr"].write("Invalid regex in pattern")
                return

            for_user = event["match"].group(1)
            if self._closest_setting(event, "sed-sender-only", False):
                for_user = event["user"].nickname

            with utils.deadline():
                match = event["target"].buffer.find(pattern, from_self=False,
                    for_user=for_user, not_pattern=REGEX_SED)

            if match:
                replace = sed_split[2]
                replace = replace.replace("\\/", "/")
                replace = re.sub(SED_AMPERSAND, match.match, replace)
                replace = utils.irc.bold(replace)

                new_message = re.sub(pattern, replace, match.line.message,
                    count)
                if match.line.action:
                    prefix = "* %s" % match.line.sender
                else:
                    prefix = "<%s>" % match.line.sender
                event["stdout"].write("%s %s" % (prefix, new_message))
