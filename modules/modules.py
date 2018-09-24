import ModuleManager

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot

        events.on("received.command.loadmodule").hook(self.load,
            min_args=1, permission="load-module", help="Load a module",
            usage="<module-name>")
        events.on("received.command.unloadmodule").hook(self.unload,
            min_args=1, permission="unload-module", help="Unload a module",
            usage="<module-name>")

        events.on("received.command.reloadmodule").hook(self.reload,
            min_args=1, permission="reload-module", help="Reoad a module",
            usage="<module-name>")

        events.on("received.command.reloadallmodules").hook(self.reload_all,
            permission="reload-module", help="Reload all modules")

        events.on("received.command.enablemodule").hook(self.enable,
            min_args=1, permission="enable-module", help="Enable a module",
            usage="<module-name>")
        events.on("received.command.disablemodule").hook(self.disable,
            min_args=1, permission="disable-module", help="Disable a module",
            usage="<module-name>")

    def load(self, event):
        name = event["args_split"][0].lower()
        if name in self.bot.modules.modules:
            event["stderr"].write("Module '%s' is already loaded" % name)
            return
        self.bot.modules.load_module(name)
        event["stdout"].write("Loaded '%s'" % name)

    def unload(self, event):
        name = event["args_split"][0].lower()
        if not name in self.bot.modules.modules:
            event["stderr"].write("Module '%s' isn't loaded" % name)
            return
        self.bot.modules.unload_module(name)
        event["stdout"].write("Unloaded '%s'" % name)

    def _reload(self, name):
        self.bot.modules.unload_module(name)
        self.bot.modules.load_module(name)

    def reload(self, event):
        name = event["args_split"][0].lower()
        try:
            self._reload(name)
        except ModuleManager.ModuleNotFoundException:
            event["stderr"].write("Module '%s' isn't loaded" % name)
            return
        event["stdout"].write("Reloaded '%s'" % name)

    def reload_all(self, event):
        reloaded = []
        failed = []
        for name in list(self.bot.modules.modules.keys()):
            try:
                self._reload(name)
            except ModuleWarning:
                continue
            except:
                failed.append(name)
                continue
            reloaded.append(name)

        if reloaded and failed:
            event["stdout"].write("Reloaded %d modules, %d failed" % (
                len(reloaded), len(failed)))
        elif failed:
            event["stdout"].write("Failed to reload all modules")
        else:
            event["stdout"].write("Reloaded %d modules" % len(reloaded))

    def enable(self, event):
        name = event["args_split"][0].lower()
        blacklist = self.bot.get_setting("module-blacklist", [])
        if not name in blacklist:
            event["stderr"].write("Module '%s' isn't disabled" % name)
            return

        blacklist.remove(name)
        event["stdout"].write("Module '%s' has been enabled and can now "
            "be loaded" % name)

    def disable(self, event):
        name = event["args_split"][0].lower()
        and_unloaded = ""
        if name in self.bot.modules.modules:
            self.bot.modules.unload_module(name)
            and_unloaded = " and unloaded"

        blacklist = self.bot.get_setting("module-blacklist", [])
        if name in blacklist:
            event["stderr"].write("Module '%s' is already disabled" % name)
            return

        blacklist.append(name)
        self.bot.set_setting("module-blacklist", blacklist)
        event["stdout"].write("Module '%s' has been disabled%s" % (
            name, and_unloaded))
