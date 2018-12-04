from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _catch(self, name, func):
        try:
            func()
        except ModuleManager.ModuleNotFoundException:
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

        self._catch(name, lambda: self.bot.modules.load_module(self.bot, name))
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
        self.bot.modules.load_module(self.bot, name)

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
        reloaded = []
        failed = []
        for name in list(self.bot.modules.modules.keys()):
            try:
                self._reload(name)
            except ModuleManager.ModuleWarning:
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

    @utils.hook("received.command.enablemodule", min_args=1)
    def enable(self, event):
        """
        :help: Remove a module from the module blacklist
        :usage: <module name>
        :permission: enable-module
        """
        name = event["args_split"][0].lower()
        blacklist = self.bot.get_setting("module-blacklist", [])
        if not name in blacklist:
            raise utils.EventError("Module '%s' isn't disabled" % name)

        blacklist.remove(name)
        event["stdout"].write("Module '%s' has been enabled and can now "
            "be loaded" % name)

    @utils.hook("received.command.disablemodule", min_args=1)
    def disable(self, event):
        """
        :help: Add a module to the module blacklist
        :usage: <module name>
        :permission: disable-module
        """
        name = event["args_split"][0].lower()
        and_unloaded = ""
        if name in self.bot.modules.modules:
            self.bot.modules.unload_module(name)
            and_unloaded = " and unloaded"

        blacklist = self.bot.get_setting("module-blacklist", [])
        if name in blacklist:
            raise utils.EventError("Module '%s' is already disabled" % name)

        blacklist.append(name)
        self.bot.set_setting("module-blacklist", blacklist)
        event["stdout"].write("Module '%s' has been disabled%s" % (
            name, and_unloaded))
