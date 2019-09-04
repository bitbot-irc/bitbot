from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
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
