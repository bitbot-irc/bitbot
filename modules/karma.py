import re, time

REGEX_KARMA = re.compile("(.*)(\+{2,}|\-{2,})")
KARMA_DELAY_SECONDS = 3

class Module(object):
    def __init__(self, bot):
        bot.events.on("new").on("user").hook(self.new_user)
        bot.events.on("received").on("message").on("channel").hook(
            self.channel_message)
        bot.events.on("received").on("command").on("karma").hook(
            self.karma, help="Get your or someone else's karma")

    def new_user(self, event):
        event["user"].last_karma = None

    def channel_message(self, event):
        match = re.match(REGEX_KARMA, event["message"])
        if match:
            if not event["user"].last_karma or (time.time()-event["user"
                    ].last_karma) >= KARMA_DELAY_SECONDS:
                positive = match.group(2)[0] == "+"
                setting = "karma-%s" % match.group(1).strip()
                karma = event["server"].get_setting(setting, 0)
                if positive:
                    karma += 1
                else:
                    karma -= 1
                if karma:
                    event["server"].set_setting(setting, karma)
                else:
                    event["server"].del_setting(setting)
                event["user"].last_karma = time.time()

    def karma(self, event):
        if event["args"]:
            target = event["args"]
        else:
            target = event["user"].nickname
        karma = event["server"].get_setting("karma-%s" % target, 0)
        event["stdout"].write("%s has %s karma" % (target, karma))
