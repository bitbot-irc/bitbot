#--depends-on check_mode
#--depends-on commands
#--depends-on permissions

from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    _name = "ChanAccess"

    def _has_channel_access(self, target, user, require_access):
        access = target.get_user_setting(user.get_id(), "access", [])
        identified = self.exports.get_one("is-identified")(user)

        return ((require_access in access or "*" in access
            ) and identified_account)

    def _command_check(self, event, target, require_access):
        if event["is_channel"]:
            if require_access:
                if self._has_channel_access(target, event["user"],
                        require_access):
                    return utils.consts.PERMISSION_FORCE_SUCCESS, None
                else:
                    return (utils.consts.PERMISSION_ERROR,
                        "You do not have permission to do this")

    @utils.hook("preprocess.command")
    def preprocess_command(self, event):
        require_access = event["hook"].get_kwarg("require_access")
        if require_access:
            return self._command_check(event, event["target"],  require_access)

    @utils.hook("check.command.channel-access")
    def check_command(self, event):
        target = event["target"]
        access = event["request_args"][0]
        if len(event["request_args"]) > 1:
            target = event["request_args"][0]
            access = event["request_args"][1]

        return self._command_check(event, target, access)

    @utils.hook("received.command.access", min_args=1, channel_only=True)
    def access(self, event):
        """
        :help: Show/modify channel access for a user
        :usage: list <nickname>
        :usage: add <nickname> <permission1 permission2 ...>
        :usage: remove <nickname> <permission1 permission2 ...>
        :usage: set <nickname> <permission1 permission2 ...>
        :require_mode: high
        """
        subcommand = event["args_split"][0].lower()
        target = event["server"].get_user(event["args_split"][1])
        access = event["target"].get_user_setting(target.get_id(), "access", [])

        if subcommand == "list":
            event["stdout"].write("Access for %s: %s" % (target.nickname,
                " ".join(access)))
        elif subcommand == "set":
            if not len(event["args_split"]) > 2:
                raise utils.EventError("Please provide a list of permissions")
            event["target"].set_user_setting(target.get_id(), "access",
                event["args_split"][2:])
        elif subcommand == "add":
            if not len(event["args_split"]) > 2:
                raise utils.EventError("Please provide a list of permissions")
            for acc in event["args_split"][2:]:
                if acc in access:
                    raise utils.EventError("%s already has '%s' permission" % (
                        target.nickname, acc))
                access.append(acc)
            event["target"].set_user_setting(target.get_id(), "access", access)
            event["stdout"].write("Added permission to %s: %s" % (
                target.nickname, " ".join(event["args_split"][2:])))
        elif subcommand == "remove":
            if not len(event["args_split"]) > 2:
                raise utils.EventError("Please provide a list of permissions")
            for acc in event["args_split"][2:]:
                if not acc in access:
                    raise utils.EventError("%s does not have '%s' permission" %
                        (target.nickname, acc))
                access.remove(acc)
            if access:
                event["target"].set_user_setting(target.get_id(), "access",
                    access)
            else:
                event["target"].del_user_setting(target.get_id(), "access")
            event["stdout"].write("Removed permission from %s: %s" % (
                target.nickname, " ".join(event["args_split"][2:])))
        else:
            event["stderr"].write("Unknown command '%s'" % subcommand)
