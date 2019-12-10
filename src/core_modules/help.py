#--depends-on commands
from src import IRCBot, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _get_help(self, hook):
        return hook.get_kwarg("help", None) or hook.docstring.description
    def _get_usage(self, hook, command, command_prefix=""):
        command = "%s%s" % (command_prefix, command)
        usage = hook.get_kwarg("usage", None)
        if usage:
            usages = [usage]
        else:
            usages = hook.docstring.var_items.get("usage", None)

        if usages:
            return " | ".join(
                "%s %s" % (command, usage) for usage in usages)
        return usage

    def _get_hook(self, command):
        hooks = self.events.on("received.command").on(command).get_hooks()
        if hooks:
            return hooks[0]
        else:
            return None

    @utils.hook("received.command.help")
    def help(self, event):
        if event["args"]:
            command = event["args_split"][0].lower()
            hook = self._get_hook(command)

            if hook == None:
                raise utils.EventError("Unknown command '%s'" % command)
            help = self._get_help(hook)
            usage = self._get_usage(hook, command, event["command_prefix"])

            out = help
            if usage:
                out += ". Usage: %s" % usage

            if out:
                event["stdout"].write("%s: %s" % (command, out))
            else:
                event["stderr"].write("No help for %s" % command)
        else:
            modules_command = utils.irc.bold(
                "%smodules" % event["command_prefix"])
            commands_command = utils.irc.bold(
                "%scommands <module>" % event["command_prefix"])
            help_command = utils.irc.bold(
                "%shelp <command>" % event["command_prefix"])

            event["stdout"].write("I'm %s. use '%s' to list modules, "
                "'%s' to list commands and "
                "'%s' to see help text for a command" %
                (IRCBot.URL, modules_command, commands_command, help_command))

    def _all_command_hooks(self):
        all_hooks = {}
        for child_name in self.events.on("received.command").get_children():
            hooks = self.events.on("received.command").on(child_name
                ).get_hooks()
            if hooks:
                all_hooks[child_name.lower()] = hooks[0]
        return all_hooks

    @utils.hook("received.command.modules")
    def modules(self, event):
        contexts = {}
        for command, command_hook in self._all_command_hooks().items():
            if not command_hook.context in contexts:
                module = self.bot.modules.from_context(command_hook.context)
                contexts[module.context] = module.name

        modules_available = sorted(contexts.values())
        event["stdout"].write("Modules: %s" % ", ".join(modules_available))

    @utils.hook("received.command.commands", min_args=1)
    def commands(self, event):
        module_name = event["args_split"][0]
        module = self.bot.modules.from_name(module_name)
        if module == None:
            raise utils.EventError("No such module '%s'" % module_name)

        commands = []
        for command, command_hook in self._all_command_hooks().items():
            if command_hook.context == module.context:
                commands.append(command)

        event["stdout"].write("Commands for %s module: %s" % (
            module.name, ", ".join(commands)))

    @utils.hook("received.command.which")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("help", "Find where a command is provided")
    @utils.kwarg("usage", "<command>")
    def which(self, event):
        command = event["args_split"][0].lower()
        hooks = self.events.on("received.command").on(command).get_hooks()
        if not hooks:
            raise utils.EventError("Unknown command '%s'" % command)

        hook = hooks[0]
        module = self.bot.modules.from_context(hook.context)
        event["stdout"].write("%s%s is provided by %s.%s" % (
            event["command_prefix"], command, module.name,
            hook.function.__name__))

    @utils.hook("received.command.apropos")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("help", "Show commands with a given string in them")
    @utils.kwarg("usage", "<query>")
    def apropos(self, event):
        query = event["args_split"][0]
        query_lower = query.lower()

        commands = []
        for command, hook in self._all_command_hooks().items():
            if query_lower in command.lower():
                commands.append("%s%s" % (event["command_prefix"], command))
        if commands:
            event["stdout"].write("Apropos of '%s': %s" %
                (query, ", ".join(commands)))
