import re, traceback
from src import ModuleManager, utils

REGEX_SPLIT = re.compile("(?<!\\\\)/")
REGEX_SED = re.compile("^s/")

@utils.export("channelset", {"setting": "sed",
    "help": "Disable/Enable sed in a channel",
    "validate": utils.bool_or_none})
@utils.export("channelset", {"setting": "sed-sender-only",
    "help": "Disable/Enable sed only looking at the messages sent by the user",
    "validate": utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    @utils.hook("received.message.channel")
    def channel_message(self, event):
        sed_split = re.split(REGEX_SPLIT, event["message"], 3)
        if event["message"].startswith("s/") and len(sed_split) > 2:
            if event["action"] or not utils.get_closest_setting(
                    event, "sed", False):
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
                self.events.on("send.stderr").call(target=event["channel"],
                    module_name="Sed", server=event["server"],
                    message="Invalid regex in pattern")
                return
            replace = sed_split[2].replace("\\/", "/")

            for_user = event["user"].nickname if utils.get_closest_setting(
                event, "sed-sender-only", False
            ) else None
            line = event["channel"].buffer.find(pattern, from_self=False,
                for_user=for_user, not_pattern=REGEX_SED)
            if line:
                new_message = re.sub(pattern, replace, line.message, count)
                if line.action:
                    prefix = "* %s" % line.sender
                else:
                    prefix = "<%s>" % line.sender
                self.events.on("send.stdout").call(target=event[
                    "channel"], module_name="Sed", server=event["server"],
                    message="%s %s" % (prefix, new_message))
