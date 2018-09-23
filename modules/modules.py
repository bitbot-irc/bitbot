

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        self.module_name = False
        self.silent = False

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

    def reload(self, event):
        name = self.module_name if self.module_name != False else event[
            "args_split"][0].lower()
        if not name in self.bot.modules.modules:
            if self.silent == False:
                event["stderr"].write("Module '%s' isn't loaded" % name)
            return
        self.bot.modules.unload_module(name)
        self.bot.modules.load_module(name)

        if self.silent == False:
            event["stdout"].write("Reloaded '%s'" % name)

    def reload_all(self, event):
        modules_reloaded = []
        self.silent = True

        for name, value in self.bot.modules.modules.items():
            if name in modules_reloaded:
                pass

            self.module_name = name
            self.reload(event)
            modules_reloaded.append(name)

        event["stdout"].write("Reloaded modules: %s" % \
                              " ".join(modules_reloaded))

        self.silent = False
        self.module_name = False

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
