#--depends-on commands
#--depends-on permissions

from bitbot import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _catch(self, name, func):
        try:
            return func()
        except ModuleManager.ModuleNotFoundException:
            raise utils.EventError("Module '%s' not found" % name)
        except ModuleManager.ModuleNotLoadedException:
            raise utils.EventError("Module '%s' isn't loaded" % name)
        except ModuleManager.ModuleWarning as warning:
            raise utils.EventError("Module '%s' not loaded: %s" % (
                name, str(warning)))
        except Exception as e:
            raise utils.EventError("Failed to reload module '%s': %s" % (
                name, str(e)))

    @utils.hook("received.command.loadmodule", min_args=1)
    def load(self, event):
        """
        :help: Load a module
        :usage: <module name>
        :permission: load-module
        """
        name = event["args_split"][0].lower()
        if name in self.bot.modules.modules:
            raise utils.EventError("Module '%s' is already loaded" % name)
        definition = self._catch(name,
            lambda: self.bot.modules.find_module(name))

        self._catch(name, lambda: self.bot.modules.load_module(self.bot, definition))
        event["stdout"].write("Loaded '%s'" % name)

    @utils.hook("received.command.unloadmodule", min_args=1)
    def unload(self, event):
        """
        :help: Unload a module
        :usage: <module name>
        :permission: unload-module
        """
        name = event["args_split"][0].lower()
        if not name in self.bot.modules.modules:
            raise utils.EventError("Module '%s' isn't loaded" % name)

        self._catch(name, lambda: self.bot.modules.unload_module(name))
        event["stdout"].write("Unloaded '%s'" % name)

    def _reload(self, name):
        self.bot.modules.unload_module(name)
        definition = self._catch(name,
            lambda: self.bot.modules.find_module(name))
        self.bot.modules.load_module(self.bot, definition)
    @utils.hook("received.command.reloadmodule", min_args=1)
    def reload(self, event):
        """
        :help: Reload a module
        :usage: <module name>
        :permission: reload-module
        """
        name = event["args_split"][0].lower()

        self._catch(name, lambda: self._reload(name))
        event["stdout"].write("Reloaded '%s'" % name)

    @utils.hook("received.command.reloadallmodules")
    def reload_all(self, event):
        """
        :help: Reload all modules
        :permission: reload-all-modules
        """
        result = self.bot.try_reload_modules()
        if result.success:
            event["stdout"].write(result.message)
        else:
            event["stderr"].write(result.message)

    def _get_blacklist(self):
        return self.bot.config.get_list("module-blacklist")
    def _save_blacklist(self, modules):
        self.bot.config.set_list("module-blacklist", modules)
        self.bot.config.save()

    @utils.hook("received.command.enablemodule")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("help", "Remove a module from the module blacklist")
    @utils.kwarg("usage", "<module>")
    @utils.kwarg("permission", "enable-module")
    def enable(self, event):
        name = event["args_split"][0].lower()

        blacklist = self._get_blacklist()
        if not name in blacklist:
            raise utils.EventError("Module '%s' isn't disabled" % name)

        blacklist.remove(name)
        self._save_blacklist(blacklist)
        event["stdout"].write("Module '%s' has been enabled and can now "
            "be loaded" % name)

    @utils.hook("received.command.disablemodule")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("help", "Add a module to the module blacklist")
    @utils.kwarg("usage", "<module>")
    @utils.kwarg("permission", "disable-module")
    def disable(self, event):
        name = event["args_split"][0].lower()
        and_unloaded = ""
        if name in self.bot.modules.modules:
            self.bot.modules.unload_module(name)
            and_unloaded = " and unloaded"

        blacklist = self._get_blacklist()
        if name in blacklist:
            raise utils.EventError("Module '%s' is already disabled" % name)

        blacklist.append(name)
        self._save_blacklist(blacklist)
        event["stdout"].write("Module '%s' has been disabled%s" % (
            name, and_unloaded))
