import signal, sys
from src import Config, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def on_load(self):
        self._exited = False
        signal.signal(signal.SIGINT, self.SIGINT)
        signal.signal(signal.SIGUSR1, self.SIGUSR1)
        signal.signal(signal.SIGHUP, self.SIGHUP)

    def SIGINT(self, signum, frame):
        print()

    def _make_hook(self, server):
        return lambda e: self.bot.disconnect(server)

    def SIGUSR1(self, signum, frame):
        self.bot.trigger(self._reload_config)

    def SIGHUP(self, signum, frame):
        self.bot.trigger(self._SIGHUP)
    def _SIGHUP(self):
        self._reload_config()
        self._reload_modules()

    def _reload_config(self):
        self.bot.log.info("Reloading config file")
        self.bot.config.load()
        self.bot.log.info("Reloaded config file")

    def _reload_modules(self):
        self.bot.log.info("Reloading modules")

        success = []
        fail = []
        for name in list(self.bot.modules.modules.keys()):
            try:
                self.bot.modules.unload_module(name)
            except ModuleManager.ModuleWarning:
                continue
            except Exception as e:
                failed.append(name)
                continue
        load_success, load_fail = self.bot.load_modules(safe=True)
        fail.extend(load_fail)

        self.bot.log.info("Reloaded %d modules (%d failed)",
            [len(load_success), len(fail)])
