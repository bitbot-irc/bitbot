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
            event["stdout"].write("%s: %s" % (command, out))
        else:
            event["stdout"].write("I'm %s. use '%smodules' to list modules, "
                "'%scommands <module>' to list commands and "
                "'%shelp <command' to see help text for a command" %
                (IRCBot.URL, event["command_prefix"], event["command_prefix"],
                event["command_prefix"]))

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
