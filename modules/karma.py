import re, time
from src import EventManager, ModuleManager, Utils

REGEX_KARMA = re.compile("^(.*[^-+])[-+]*(\+{2,}|\-{2,})$")
KARMA_DELAY_SECONDS = 3

@Utils.export("channelset", {"setting": "karma-verbose",
    "help": "Enable/disable automatically responding to karma changes",
    "validate": Utils.bool_or_none})
@Utils.export("serverset", {"setting": "karma-nickname-only",
    "help": "Enable/disable karma being for nicknames only",
    "validate": Utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    @Utils.hook("new.user")
    def new_user(self, event):
        event["user"].last_karma = None

    @Utils.hook("received.message.channel",
        priority=EventManager.PRIORITY_MONITOR)
    def channel_message(self, event):
        match = re.match(REGEX_KARMA, event["message"].strip())
        if match and not event["action"]:
            verbose = event["channel"].get_setting("karma-verbose", False)
            nickname_only = event["server"].get_setting("karma-nickname-only",
                False)

            if not event["user"].last_karma or (time.time()-event["user"
                    ].last_karma) >= KARMA_DELAY_SECONDS:
                target = match.group(1).strip()
                if target == event["user"].name:
                    if verbose:
                        self.events.on("send.stderr").call(
                            module_name="Karma", target=event["channel"],
                            message="You cannot change your own karma")
                    return

                setting = "karma-%s" % target
                setting_target = event["server"]
                if nickname_only:
                    user = event["server"].get_user(target)
                    setting = target
                    setting_target = user
                    if not event["channel"].has_user(user):
                        return

                positive = match.group(2)[0] == "+"
                karma = event["server"].get_setting(setting, 0)
                karma += 1 if positive else -1

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
                self.events.on("send.stderr").call(module_name="Karma",
                    target=event["channel"],
                    message="Try again in a couple of seconds")

    @Utils.hook("received.command.karma")
    def karma(self, event):
        """
        :help: Get your or someone else's karma
        :usage: [target]
        """
        if event["args"]:
            target = event["args"]
        else:
            target = event["user"].nickname

        if event["server"].get_setting("karma-nickname-only", False):
            karma = event["server"].get_user(target).get_setting("karma", 0)
        else:
            karma = event["server"].get_setting("karma-%s" % target, 0)
        event["stdout"].write("%s has %s karma" % (target, karma))

    @Utils.hook("received.command.resetkarma", min_args=1)
    def reset_karma(self, event):
        """
        :help: Reset a specified karma to 0
        :usage: <target>
        :permission: resetkarme
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
