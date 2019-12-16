#--depends-on commands
#--depends-on config
#--depends-on permissions

import re, time
from bitbot import EventManager, ModuleManager, utils

KARMA_DELAY_SECONDS = 3

REGEX_WORD = re.compile(r"^([^(\s,:]+)(?:[:,]\s*)?(\+\+|--)\s*$")
REGEX_WORD_START = re.compile(r"^(\+\+|--)(?:\s*)([^(\s,:]+)\s*$")
REGEX_PARENS = re.compile(r"\(([^)]+)\)(\+\+|--)")

@utils.export("channelset", utils.BoolSetting("karma-pattern",
    "Enable/disable parsing ++/-- karma format"))
class Module(ModuleManager.BaseModule):
    def _karma_str(self, karma):
        karma_str = str(karma)
        if karma < 0:
            return utils.irc.color(str(karma), utils.consts.RED)
        elif karma > 0:
            return utils.irc.color(str(karma), utils.consts.LIGHTGREEN)
        else:
            return utils.irc.color(str(karma), utils.consts.YELLOW)

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

    def _get_target(self, server, target):
        target = target.strip()
        if not " " in target and server.has_user(target):
            return server.get_user_nickname(server.get_user(target).get_id())
        return target.lower()

    def _change_karma(self, server, sender, target, positive):
        if not self._check_throttle(sender, positive):
            return False, "Try again in a couple of seconds"

        target = self._get_target(server, target)

        setting = "karma-%s" % target
        karma = sender.get_setting(setting, 0)
        karma += 1 if positive else -1

        if karma == 0:
            sender.del_setting(setting)
        else:
            sender.set_setting(setting, karma)

        self._set_throttle(sender, positive)
        karma_str = self._karma_str(karma)

        karma_total = self._karma_str(self._get_karma(server, target))

        return True, "%s has given %s %s karma (%s total)" % (
            sender.nickname, target, karma_str, karma_total)

    @utils.hook("command.regex", pattern=REGEX_WORD)
    @utils.hook("command.regex", pattern=REGEX_PARENS)
    @utils.kwarg("command", "karma")
    def regex_word(self, event):
        if event["target"].get_setting("karma-pattern", False):
            target = event["match"].group(1)
            positive = event["match"].group(2)=="++"
            success, message = self._change_karma(
                event["server"], event["user"], target, positive)
            event["stdout" if success else "stderr"].write(message)
    @utils.hook("command.regex", pattern=REGEX_WORD_START)
    @utils.kwarg("command", "karma")
    def regex_word_start(self, event):
        if event["target"].get_setting("karma-pattern", False):
            target = event["match"].group(2)
            positive = event["match"].group(1)=="++"
            success, message = self._change_karma(
                event["server"], event["user"], target, positive)
            event["stdout" if success else "stderr"].write(message)

    @utils.hook("received.command.addpoint")
    @utils.hook("received.command.rmpoint")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("usage", "<target>")
    def changepoint(self, event):
        positive = event["command"] == "addpoint"
        success, message = self._change_karma(
            event["server"], event["user"], event["args"].strip(), positive)
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

        target = self._get_target(event["server"], target)
        karma = self._karma_str(self._get_karma(event["server"], target))

        event["stdout"].write("%s has %s karma" % (target, karma))

    def _get_karma(self, server, target):
        settings = dict(server.get_all_user_settings("karma-%s" % target))

        target_lower = server.irc_lower(target)
        if target_lower in settings:
            del settings[target_lower]

        return sum(settings.values())

    @utils.hook("received.command.resetkarma")
    @utils.kwarg("min_args", 2)
    @utils.kwarg("help", "Reset a specific karma to 0")
    @utils.kwarg("usage", "by|for <target>")
    @utils.kwarg("permission", "resetkarma")
    def reset_karma(self, event):
        subcommand = event["args_split"][0].lower()
        target = " ".join(event["args_split"][1:])

        if subcommand == "by":
            target_user = event["server"].get_user(target)
            karma = target_user.find_setting(prefix="karma-")
            print(target_user)
            print(target_user.get_id())
            for setting, _ in karma:
                target_user.del_setting(setting)

            if karma:
                event["stdout"].write("Cleared karma by %s" %
                    target_user.nickname)
            else:
                event["stderr"].write("No karma to clear by %s" %
                    target_user.nickname)
        elif subcommand == "for":
            setting = "karma-%s" % target
            karma = event["server"].get_all_user_settings(setting)
            for nickname, value in karma:
                user = event["server"].get_user(nickname)
                user.del_setting(setting)

            if karma:
                event["stdout"].write("Cleared karma for %s" % target)
            else:
                event["stderr"].write("No karma to clearfor %s" % target)
        else:
            raise utils.EventError("Unknown subcommand '%s'" % subcommand)
