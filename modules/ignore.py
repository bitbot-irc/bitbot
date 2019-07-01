#--depends-on commands
#--depends-on permissions

from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _user_ignored(self, user):
        return user.get_setting("ignore", False)
    def _user_command_ignored(self, user, command):
        return user.get_setting("ignore-%s" % command, False)
    def _server_command_ignored(self, server, command):
        return server.get_setting("ignore-%s" % command, False)

    @utils.hook("received.message.private")
    @utils.hook("received.message.channel")
    def message(self, event):
        if self._user_ignored(event["user"]):
            event.eat()

    @utils.hook("preprocess.command")
    def preprocess_command(self, event):
        if self._user_command_ignored(event["user"], event["command"]):
            return utils.consts.PERMISSION_HARD_FAIL
        elif self._server_command_ignored(event["server"], event["command"]):
            return utils.consts.PERMISSION_HARD_FAIL

    @utils.hook("received.command.ignore", min_args=1)
    def ignore(self, event):
        """
        :help: Ignore commands from a given user
        :usage: <nickname> [command]
        :permission: ignore
        """
        setting = "ignore"
        for_str = ""
        if len(event["args_split"]) > 1:
            command = event["args_split"][1].lower()
            setting = "ignore-%s" % command
            for_str = " for '%s'" % command

        user = event["server"].get_user(event["args_split"][0])
        if user.get_setting(setting, False):
            event["stderr"].write("I'm already ignoring '%s'%s" %
                (user.nickname, for_str))
        else:
            user.set_setting(setting, True)
            event["stdout"].write("Now ignoring '%s'%s" %
                (user.nickname, for_str))

    @utils.hook("received.command.unignore", min_args=1)
    def unignore(self, event):
        """
        :help: Unignore commands from a given user
        :usage: <nickname> [command]
        :permission: unignore
        """
        setting = "ignore"
        for_str = ""
        if len(event["args_split"]) > 1:
            command = event["args_split"][1].lower()
            setting = "ignore-%s" % command
            for_str = " for '%s'" % command

        user = event["server"].get_user(event["args_split"][0])
        if not user.get_setting(setting, False):
            event["stderr"].write("I'm not ignoring '%s'%s" %
                (user.nickname, for_str))
        else:
            user.del_setting(setting)
            event["stdout"].write("Removed ignore for '%s'%s" %
                (user.nickname, for_str))

    @utils.hook("received.command.serverignore", min_args=1)
    def server_ignore(self, event):
        """
        :permission: server-ignore
        """
        command = event["args_split"][0].lower()
        setting = "ignore-%s" % command

        if event["server"].get_setting(setting, False):
            event["stderr"].write("I'm already ignoring '%s' for %s" %
                (command, str(event["server"])))
        else:
            event["server"].set_setting(setting, True)
            event["stdout"].write("Now ignoring '%s' for %s" %
                (command, str(event["server"])))

    @utils.hook("received.command.serverunignore", min_args=1)
    def server_unignore(self, event):
        """
        :permission: server-unignore
        """
        command = event["args_split"][0].lower()
        setting = "ignore-%s" % command

        if not event["server"].get_setting(setting, False):
            event["stderr"].write("I'm not ignoring '%s' for %s" %
                (command, str(event["server"])))
        else:
            event["server"].del_setting(setting)
            event["stdout"].write("No longer ignoring '%s' for %s" %
                (command, str(event["server"])))

