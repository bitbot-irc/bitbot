#--depends-on commands
from src import EventManager, ModuleManager, utils

SETTING_PREFIX = "command-alias-"

class Module(ModuleManager.BaseModule):
    def _arg_replace(self, s, args_split, kwargs):
        vars = {}
        for i in range(len(args_split)):
            vars[str(i)] = args_split[i]
            vars["%d-" % i] = " ".join(args_split[i:])
        vars["-"] = " ".join(args_split)
        vars.update(kwargs)
        return utils.parse.format_token_replace(s, vars)

    def _get_alias(self, server, target, command):
        setting = "%s%s" % (SETTING_PREFIX, command)
        command = self.bot.get_setting(setting,
            server.get_setting(setting,
            target.get_setting(setting, None)))
        if not command == None:
            command, _, args = command.partition(" ")
            return command, args
        return None
    def _get_aliases(self, targets):
        alias_list = []
        for target in targets:
            alias_list += target.find_settings(prefix=SETTING_PREFIX)

        aliases = {}
        for alias, command in alias_list:
            alias = alias.replace(SETTING_PREFIX, "", 1)
            if not alias in aliases:
                aliases[alias] = command
        return aliases

    @utils.hook("get.command")
    @utils.kwarg("priority", EventManager.PRIORITY_URGENT)
    def get_command(self, event):
        alias = self._get_alias(event["server"], event["target"],
            event["command"].command)
        if not alias == None:
            alias, alias_args = alias

            given_args = []
            if event["command"].args:
                given_args = event["command"].args.split(" ")

            event["command"].command = alias
            event["command"].args = self._arg_replace(alias_args, given_args,
                {"NICK": event["user"].nickname})

    @utils.hook("received.command.alias",
        permission="alias")
    @utils.hook("received.command.balias",
        permission="balias")
    @utils.hook("received.command.calias",
        require_mode="o", require_access="alias")

    @utils.spec("!'list ?<alias>wordlower")
    @utils.spec("!'add !<alias>wordlower !<command>wordlower ?<args>string")
    @utils.spec("!'remove !<alias>wordlower")
    @utils.kwarg("remove_empty", False)
    def alias(self, event):
        target = event["server"]
        if event["command"] == "calias":
            if not event["is_channel"]:
                raise utils.EventError("%scalias can only be used in-channel"
                    % event["command_prefix"])
            target = event["target"]
        elif event["command"] == "balias":
            target = self.bot

        subcommand = event["spec"][0]
        alias = event["spec"][1]
        if subcommand == "list":
            if alias:
                setting = target.get_setting(f"{SETTING_PREFIX}{alias}", None)

                if setting == None:
                    raise utils.EventError("I don't have an '%s' alias" % alias)
                prefix = event["command_prefix"]
                event["stdout"].write(f"{prefix}{alias}: {prefix}{setting}")
            else:
                aliases = self._get_aliases([target])
                event["stdout"].write("Available aliases: %s" %
                    ", ".join(sorted(aliases.keys())))

        elif subcommand == "add":
            command = event["spec"][2].lower()
            args = event["spec"][3]
            if args:
                command = f"{command} {args}"

            target.set_setting("%s%s" % (SETTING_PREFIX, alias), command)
            event["stdout"].write("Added '%s' alias" % alias)

        elif subcommand == "remove":
            setting = f"{SETTING_PREFIX}{alias}"
            if target.get_setting(setting, None) == None:
                raise utils.EventError("I don't have an '%s' alias" % alias)

            target.del_setting(setting)
            event["stdout"].write("Removed '%s' alias" % alias)

        else:
            raise utils.EventError("Unknown subcommand '%s'" % subcommand)
