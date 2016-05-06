import re, traceback
import Utils

REGEX_SPLIT = re.compile("(?<!\\\\)/")
REGEX_SED = re.compile("^s/")

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("boot").on("done").hook(self.boot_done)
        bot.events.on("received").on("message").on("channel").hook(
            self.channel_message)

    def boot_done(self, event):
        self.bot.events.on("postboot").on("configure").on(
            "channelset").call(setting="sed",
            help="Disable/Enable sed in a channel",
            validate=Utils.bool_or_none)

    def channel_message(self, event):
        if event["action"] or not Utils.get_closest_setting(event, "sed", True):
            return
        sed_split = re.split(REGEX_SPLIT, event["message"], 3)
        if event["message"].startswith("s/") and len(sed_split) > 2:
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
                self.bot.events.on("send").on("stderr").call(target=event[
                    "channel"], module_name="Sed", server=event["server"],
                    message="Invalid regex in pattern")
                return
            replace = sed_split[2].replace("\\/", "/")

            line = event["channel"].log.find(pattern, from_self=False, not_pattern=REGEX_SED)
            if line:
                new_message = re.sub(pattern, replace, line.message, count)
                if line.action:
                    prefix = "* %s" % line.sender
                else:
                    prefix = "<%s>" % line.sender
                self.bot.events.on("send").on("stdout").call(target=event[
                    "channel"], module_name="Sed", server=event["server"],
                    message="%s %s" % (prefix, new_message))
