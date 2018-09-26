import re, time
from src import EventManager, Utils

REGEX_KARMA = re.compile("^(.*[^-+])[-+]*(\+{2,}|\-{2,})$")
KARMA_DELAY_SECONDS = 3

class Module(object):
    def __init__(self, bot, events, exports):
        self.events = events
        exports.add("channelset", {"setting": "karma-verbose",
            "help": "Disable/Enable automatically responding to "
            "karma changes", "validate": Utils.bool_or_none})

    @Utils.hook("new.user")
    def new_user(self, event):
        event["user"].last_karma = None

    @Utils.hook("received.message.channel",
        priority=EventManager.PRIORITY_MONITOR)
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
                        self.events.on("send.stdout").call(
                            module_name="Karma", target=event["channel"],
                            message="%s now has %d karma" % (target, karma))
                    event["user"].last_karma = time.time()
                elif verbose:
                    if target:
                        self.events.on("send.stderr").call(
                            module_name="Karma", target=event["channel"],
                            message="You cannot change your own karma")
            elif verbose:
                self.events.on("send.stderr").call(module_name="Karma",
                    target=event["channel"],
                    message="Try again in a couple of seconds")

    @Utils.hook("received.command.karma", usage="[target]")
    def karma(self, event):
        """
        Get your or someone else's karma
        """
        if event["args"]:
            target = event["args"]
        else:
            target = event["user"].nickname
        karma = event["server"].get_setting("karma-%s" % target, 0)
        event["stdout"].write("%s has %s karma" % (target, karma))

    @Utils.hook("received.command.resetkarma", permission="resetkarma",
        min_args=1, usage="<target>")
    def reset_karma(self, event):
        """
        Reset a specified karma to 0
        """
        setting = "karma-%s" % event["args_split"][0]
        karma = event["server"].get_setting(setting, 0)
        if karma == 0:
            event["stderr"].write("%s already has 0 karma" % event[
                "args_split"][0])
        else:
            event["server"].del_setting(setting)
            event["stdout"].write("Reset karma for %s" % event[
                "args_split"][0])
