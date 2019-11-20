#--depends-on commands
import re
from src import EventManager, ModuleManager, utils

REGEX_ARG_NUMBER = re.compile(r"\$(?:(\d+)(-?)|(-))")
SETTING_PREFIX = "alias-"

class Module(ModuleManager.BaseModule):
    def _arg_replace(self, s, args_split):
        for match in REGEX_ARG_NUMBER.finditer(s):
            if match.group(1):
                index = int(match.group(1))
                continuous = match.group(2) == "-"
                if index >= len(args_split):
                    raise IndexError("Unknown alias arg index")
            else:
                index = 0
                continuous = True

            if continuous:
                replace = " ".join(args_split[index:])
            else:
                replace = args_split[index]
            s = s.replace(match.group(0), replace)
        return s

    def _get_alias(self, server, target, command):
        setting = "%s%s" % (SETTING_PREFIX, command)
        alias = self.bot.get_setting(setting,
            server.get_setting(setting,
            target.get_setting(setting, None)))
        if not alias == None:
            alias, _, args = alias.partition(" ")
            return alias, args
        return None
    def _get_aliases(self, targets):
        alias_list = []
        for target in targets:
            alias_list += target.find_settings(prefix=SETTING_PREFIX)

        aliases = {}
        for alias in alias_list:
            alias, _, args = alias.partition(" ")
            if not alias in aliases:
                aliases[alias] = args or None
        return aliases

    @utils.hook("get.command")
    @utils.kwarg("priority", EventManager.PRIORITY_URGENT)
    def get_command(self, event):
        alias = self._get_alias(event["server"], event["target"],
            event["command"].command)
        if not alias == None:
            alias, alias_args = alias
            event["command"].command = alias
            event["command"].args = self._arg_replace(alias_args,
                event["command"].args.split(" "))

    @utils.hook("received.command.alias")
    @utils.hook("received.command.calias")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("usage", "list")
    @utils.kwarg("usage", "add <alias> <command> [arg1 [arg2 ...]]")
    @utils.kwarg("usage", "remove <alias>")
    @utils.kwarg("remove_empty", False)
    def alias(self, event):
        target = event["server"]
        if event["command"] == "calias":
            if not event["is_channel"]:
                raise utils.EventError("%scalias can only be used in-channel"
                    % event["command_prefix"])
            target = event["target"]

        subcommand = event["args_split"][0].lower()
        if subcommand == "list":
            aliases = self._get_aliases([target])
            event["stdout"].write("Available aliases: %s" %
                ", ".join(sorted(aliases.keys())))

        elif subcommand == "show":
            if not len(event["args_split"]) > 1:
                raise utils.EventError("Please provide an alias to remove")

            alias = event["args_split"][0].lower()
            setting = target.get_setting("%s%s" % (SETTING_PREFIX, alias), None)

            if setting == None:
                raise utils.EventError("I don't have an '%s' alias" % alias)
            prefix = event["command_prefix"]
            event["stdout"].write(f"{prefix}{alias}: {prefix}{setting}")

        elif subcommand == "add":
            if not len(event["args_split"]) > 2:
                raise utils.EventError("Please provide an alias and a command")

            alias = event["args_split"][1].lower()
            command = event["args_split"][2].lower()
            command = " ".join([command]+event["args_split"][3:])
            target.set_setting("%s%s" % (SETTING_PREFIX, alias), command)

            event["stdout"].write("Added '%s' alias" % alias)

        elif subcommand == "remove":
            if not len(event["args_split"]) > 1:
                raise utils.EventError("Please provide an alias to remove")

            alias = event["args_split"][1].lower()
            setting = "%s%s" % (SETTING_PREFIX, alias)
            if target.get_setting(setting, None) == None:
                raise utils.EventError("I don't have an '%s' alias" % alias)

            target.del_setting(setting)
            event["stdout"].write("Removed '%s' alias" % alias)
