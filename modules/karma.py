#--depends-on commands
#--depends-on config
#--depends-on permissions

import re, time
from src import EventManager, ModuleManager, utils

WORD_STOP = [",", ":"]
KARMA_DELAY_SECONDS = 3

REGEX_KARMA = re.compile(r"^(?:(\S+:) )?(.*)(\+{2}|\-{2})$")

@utils.export("channelset", utils.BoolSetting("karma-pattern",
    "Enable/disable parsing ++/-- karma format"))
@utils.export("serverset", utils.BoolSetting("karma-nickname-only",
    "Enable/disable karma being for nicknames only"))
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
        event["user"]._last_positive_karma = None
        event["user"]._last_negative_karma = None

    def _check_throttle(self, user, positive):
        timestamp = None
        if positive:
            timestamp = user._last_positive_karma
        else:
            timestamp = user._last_negative_karma
        return timestamp == None or (time.time()-timestamp
            ) >= KARMA_DELAY_SECONDS
    def _set_throttle(self, user, positive):
        if positive:
            user._last_positive_karma = time.time()
        else:
            user._last_negative_karma = time.time()


    def _karma(self, server, sender, target, positive):
        if self._check_throttle(sender, positive):
            nickname_only = server.get_setting("karma-nickname-only", False)

            if server.irc_lower(target) == sender.name:
                return False, "You cannot change your own karma"

            setting = "karma-%s" % target
            setting_target = server
            if nickname_only:
                user = server.get_user(target, create=False)
                if user == None:
                    return False, "No such user"
                setting = "karma"
                setting_target = user

            karma = setting_target.get_setting(setting, 0)
            karma += 1 if positive else -1

            if not karma == 0:
                setting_target.set_setting(setting, karma)
            else:
                setting_target.del_setting(setting)

            karma_str = self._karma_str(karma)
            self._set_throttle(sender, positive)
            return True, "%s now has %s karma" % (target, karma_str)
        else:
            return False, "Try again in a couple of seconds"

    @utils.hook("command.regex")
    @utils.kwarg("command", "karma")
    @utils.kwarg("pattern", REGEX_KARMA)
    def channel_message(self, event):
        pattern = event["target"].get_setting("karma-pattern", False)
        if pattern:
            positive = event["match"].group(3)[0] == "+"

            target = event["match"].group(2).strip().rstrip("".join(WORD_STOP))
            if event["match"].group(1):
                if not target:
                    target = event["match"].group(1)[1:]
                elif not event["server"].has_user(event["match"].group(1)[:-1]):
                    target = "%s %s" % (event["match"].group(1), target)

            if target:
                success, message = self._karma(event["server"], event["user"],
                    target, positive)
                event["stdout" if success else "stderr"].write(message)

    @utils.hook("received.command.addpoint")
    @utils.hook("received.command.rmpoint")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("usage", "<target>")
    def changepoint(self, event):
        positive = event["command"] == "addpoint"
        success, message = self._karma(event["server"], event["user"],
            event["args"].strip(), positive)
        event["stdout" if success else "stderr"].write(message)

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
        :permission: resetkarma
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
