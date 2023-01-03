#--depends-on commands
#--depends-on permissions

from src import EventManager, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _user_ignored(self, user):
        return user.get_setting("ignore", False)
    def _user_command_ignored(self, user, command):
        return user.get_setting("ignore-%s" % command, False)
    def _user_channel_ignored(self, channel, user):
        return channel.get_user_setting(user.get_id(), "ignore", False)
    def _server_command_ignored(self, server, command):
        return server.get_setting("ignore-%s" % command, False)
    def _channel_command_ignored(self, channel, command):
        return channel.get_setting("ignore-command-%s" % command, False)

    def _is_command_ignored(self, event):
        if self._user_command_ignored(event["user"], event["command"]):
            return True
        elif self._server_command_ignored(event["server"], event["command"]):
            return True
        elif event["is_channel"] and self._channel_command_ignored(event["target"], event["command"]):
            return True

    def _is_valid_command(self, command):
        hooks = self.events.on("received.command").on(command).get_hooks()
        if hooks:
            return True
        else:
            return False

    @utils.hook("received.message.private")
    @utils.hook("received.message.channel")
    @utils.hook("received.notice.private")
    @utils.hook("received.notice.channel")
    @utils.kwarg("priority", EventManager.PRIORITY_HIGH)
    def message(self, event):
        if self._user_ignored(event["user"]):
            event.eat()
        elif event["is_channel"] and self._user_channel_ignored(event["target"],
                event["user"]):
            event.eat()

    @utils.hook("preprocess.command")
    def preprocess_command(self, event):
        if self._user_ignored(event["user"]):
            return utils.consts.PERMISSION_HARD_FAIL, None
        elif event["is_channel"] and self._user_channel_ignored(event["target"],
                event["user"]):
            return utils.consts.PERMISSION_HARD_FAIL, None
        elif self._is_command_ignored(event):
            return utils.consts.PERMISSION_HARD_FAIL, None

    @utils.hook("received.command.ignore", min_args=1)
    @utils.kwarg("permission", "ignore")
    @utils.kwarg("help", "Ignore commands from a given user")
    @utils.spec("?duration !<nickname>ouser ?<command>wordlower")
    def ignore(self, event):
        setting = "ignore"
        for_str = ""
        if event["spec"][2]:
            setting = "ignore-%s" % event["spec"][2]
            for_str = " for '%s'" % event["spec"][2]

        user = event["spec"][1]
        if user.get_setting(setting, False):
            event["stderr"].write("I'm already ignoring '%s'%s" %
                (user.nickname, for_str))
        else:
            user.set_setting(setting, True)
            event["stdout"].write("Now ignoring '%s'%s" %
                (user.nickname, for_str))

        time = event["spec"][0]
        if not time == None:
            self.timers.add_persistent("unignore", time,
                user_id=user.get_id(), setting=setting)
    @utils.hook("timer.unignore")
    def _timer_unignore(self, event):
        self.bot.database.user_settings.delete(
            event["user_id"], event["setting"])

    @utils.hook("received.command.unignore")
    @utils.kwarg("help", "Unignore commands from a given user")
    @utils.kwarg("permission", "unignore")
    @utils.spec("!<nickname>ouser ?<command>wordlower")
    def unignore(self, event):
        setting = "ignore"
        for_str = ""
        if event["spec"][1]:
            command = event["spec"][1]
            setting = "ignore-%s" % command
            for_str = " for '%s'" % command

        user = event["spec"][0]
        if not user.get_setting(setting, False):
            event["stderr"].write("I'm not ignoring '%s'%s" %
                (user.nickname, for_str))
        else:
            user.del_setting(setting)
            event["stdout"].write("Removed ignore for '%s'%s" %
                (user.nickname, for_str))

    @utils.hook("received.command.cignore",
        help="Ignore a user in this channel")
    @utils.hook("received.command.cunignore",
        help="Unignore a user in this channel")
    @utils.kwarg("channel_only", True)
    @utils.kwarg("min_args", 1)
    @utils.kwarg("usage", "<nickname>")
    @utils.kwarg("permission", "cignore")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "high,cignore")
    def cignore(self, event):
        remove = event["command"] == "cunignore"

        target_user = event["server"].get_user(event["args_split"][0])
        is_ignored = event["target"].get_user_setting(target_user.get_id(),
            "ignore", False)

        if remove:
            if not is_ignored:
                raise utils.EventError("I'm not ignoring %s in this channel" %
                    target_user.nickname)
            event["target"].del_user_setting(target_user.get_id(), "ignore")
            event["stdout"].write("Unignored %s" % target_user.nickname)
        else:
            if is_ignored:
                raise utils.EventError("I'm already ignoring %s in this channel"
                    % target_user.nickname)
            event["target"].set_user_setting(target_user.get_id(), "ignore",
                True)
            event["stdout"].write("Ignoring %s" % target_user.nickname)

    @utils.hook("received.command.ignorecommand",
        help="Ignore a command in this channel")
    @utils.hook("received.command.unignorecommand",
        help="Unignore a command in this channel")
    @utils.kwarg("channel_only", True)
    @utils.kwarg("min_args", 1)
    @utils.kwarg("usage", "<command>")
    @utils.kwarg("permission", "cignore")
    @utils.kwarg("require_mode", "o")
    @utils.kwarg("require_access", "high,cignore")
    def cignore_command(self, event):
        remove = event["command"] == "unignorecommand"

        command = event["args_split"][0]
        if not self._is_valid_command(command):
            raise utils.EventError("Unknown command '%s'" % command)
        is_ignored = self._channel_command_ignored(event["target"], command)

        if remove:
            if not is_ignored:
                raise utils.EventError("I'm not ignoring '%s' in this channel" %
                    target_user.nickname)
            event["target"].del_setting("ignore-command-%s" % command)
            event["stdout"].write("Unignored '%s' command" % command)
        else:
            if is_ignored:
                raise utils.EventError("I'm already ignoring '%s' in this channel"
                    % command)
            event["target"].set_setting("ignore-command-%s" % command, True)
            event["stdout"].write("Ignoring '%s' command" % command)


    @utils.hook("received.command.serverignore")
    @utils.kwarg("help", "Ignore a command on the current server")
    @utils.kwarg("permission", "serverignore")
    @utils.spec("!<command>wordlower")
    def server_ignore(self, event):
        command = event["spec"][0]
        setting = "ignore-%s" % command

        if event["server"].get_setting(setting, False):
            event["stderr"].write("I'm already ignoring '%s' for %s" %
                (command, str(event["server"])))
        else:
            event["server"].set_setting(setting, True)
            event["stdout"].write("Now ignoring '%s' for %s" %
                (command, str(event["server"])))

    @utils.hook("received.command.serverunignore")
    @utils.kwarg("help", "Unignore a command on the current server")
    @utils.kwarg("permission", "serverunignore")
    @utils.spec("!<command>wordlower")
    def server_unignore(self, event):
        command = event["spec"][0]
        setting = "ignore-%s" % command

        if not event["server"].get_setting(setting, False):
            event["stderr"].write("I'm not ignoring '%s' for %s" %
                (command, str(event["server"])))
        else:
            event["server"].del_setting(setting)
            event["stdout"].write("No longer ignoring '%s' for %s" %
                (command, str(event["server"])))
