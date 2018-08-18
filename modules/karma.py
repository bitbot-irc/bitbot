import re, time
import Utils

REGEX_KARMA = re.compile("(.*)(\+{2,}|\-{2,})$")
KARMA_DELAY_SECONDS = 3

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("new").on("user").hook(self.new_user)
        bot.events.on("received").on("message").on("channel").hook(
            self.channel_message)
        bot.events.on("received").on("command").on("karma").hook(
            self.karma, help="Get your or someone else's karma",
            usage="[target]")
        bot.events.on("received").on("command").on("resetkarma").hook(
            self.reset_karma, permission="resetkarma",
            min_args=1, help="Reset a specified karma to 0",
            usage="<target>")

        bot.events.on("postboot").on("configure").on(
            "channelset").call(setting="karma-verbose",
            help="Disable/Enable automatically responding to karma changes",
            validate=Utils.bool_or_none)

    def new_user(self, event):
        event["user"].last_karma = None

    def channel_message(self, event):
        match = re.match(REGEX_KARMA, event["message"].strip())
        if match and not event["action"]:
            verbose = event["channel"].get_setting("karma-verbose", False)
            if not event["user"].last_karma or (time.time()-event["user"
                    ].last_karma) >= KARMA_DELAY_SECONDS:
                target = match.group(1).lower().strip()
                if not target == event["user"].name and target:
                    positive = match.group(2)[0] == "+"
                    setting = "karma-%s" % target
                    karma = event["server"].get_setting(setting, 0)
                    if positive:
                        karma += 1
                    else:
                        karma -= 1
                    if karma:
                        event["server"].set_setting(setting, karma)
                    else:
                        event["server"].del_setting(setting)
                    if verbose:
                        self.bot.events.on("send").on("stdout").call(
                            module_name="Karma", target=event["channel"],
                            message="%s now has %d karma" % (target, karma))
                    event["user"].last_karma = time.time()
                elif verbose:
                    if target:
                        self.bot.events.on("send").on("stderr").call(module_name="Karma",
                            target=event["channel"], message="You cannot change your own karma")
            elif verbose:
                event["stderr"].write("Try again in a couple of seconds")
    def karma(self, event):
        if event["args"]:
            target = event["args"]
        else:
            target = event["user"].nickname
        karma = event["server"].get_setting("karma-%s" % target, 0)
        event["stdout"].write("%s has %s karma" % (target, karma))

    def reset_karma(self, event):
        setting = "karma-%s" % event["args_split"][0]
        karma = event["server"].get_setting(setting, 0)
        if karma == 0:
            event["stderr"].write("%s already has 0 karma" % event[
                "args_split"][0])
        else:
            event["server"].del_setting(setting)
            event["stdout"].write("Reset karma for %s" % event[
                "args_split"][0])
