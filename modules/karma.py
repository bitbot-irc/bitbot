import re, time
from src import EventManager, ModuleManager, utils

REGEX_KARMA = re.compile("^(.*[^-+])[-+]*(\+{2,}|\-{2,})$")
WORD_STOP = [",", ":"]
KARMA_DELAY_SECONDS = 3

@utils.export("channelset", {"setting": "karma-verbose",
    "help": "Enable/disable automatically responding to karma changes",
    "validate": utils.bool_or_none})
@utils.export("serverset", {"setting": "karma-nickname-only",
    "help": "Enable/disable karma being for nicknames only",
    "validate": utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    def _karma_str(self, karma):
        karma_str = str(karma)
        if karma < 0:
            return utils.irc.color(str(karma), utils.consts.RED)
        elif karma > 0:
            return utils.irc.color(str(karma), utils.consts.LIGHTGREEN)
        return str(karma)

    @utils.hook("new.user")
    def new_user(self, event):
        event["user"].last_karma = None

    @utils.hook("command.regex")
    def channel_message(self, event):
        """
        :command: karma
        :pattern: ^(.*[^-+])[-+]*(\+{2,}|\-{2,})$
        """
        verbose = event["target"].get_setting("karma-verbose", False)
        nickname_only = event["server"].get_setting("karma-nickname-only",
            False)

        if not event["user"].last_karma or (time.time()-event["user"
                ].last_karma) >= KARMA_DELAY_SECONDS:
            target = event["match"].group(1).strip().rstrip("".join(WORD_STOP))
            if event["server"].irc_lower(target) == event["user"].name:
                if verbose:
                    event["stderr"].write("You cannot change your own karma")
                return

            setting = "karma-%s" % target
            setting_target = event["server"]
            if nickname_only:
                user = event["server"].get_user(target)
                setting = "karma"
                setting_target = user
                if not event["target"].has_user(user):
                    return

            positive = event["match"].group(2)[0] == "+"
            karma = setting_target.get_setting(setting, 0)
            karma += 1 if positive else -1

            if not karma == 0:
                setting_target.set_setting(setting, karma)
            else:
                setting_target.del_setting(setting)

            karma_str = self._karma_str(karma)
            if verbose:
                event["stdout"].write(
                    "%s now has %s karma" % (target, karma_str))
            event["user"].last_karma = time.time()
        elif verbose:
            event["stderr"].write("Try again in a couple of seconds")

    @utils.hook("received.command.karma")
    def karma(self, event):
        """
        :help: Get your or someone else's karma
        :usage: [target]
        """
        if event["args"]:
            target = event["args"]
        else:
            target = event["user"].nickname
        target = target.strip()

        if event["server"].get_setting("karma-nickname-only", False):
            karma = event["server"].get_user(target).get_setting("karma", 0)
        else:
            karma = event["server"].get_setting("karma-%s" % target, 0)
        karma_str = self._karma_str(karma)
        event["stdout"].write("%s has %s karma" % (target, karma_str))

    @utils.hook("received.command.resetkarma", min_args=1)
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
