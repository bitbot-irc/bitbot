import signal
from src import Config, ModuleManager, utils

@utils.export("serverset", {"setting": "quit-quote",
    "help": "Set whether I pick a random quote to /quit with",
    "validate": utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    def on_load(self):
        self._exited = False
        signal.signal(signal.SIGINT, self.SIGINT)
        signal.signal(signal.SIGUSR1, self.SIGUSR1)

    def SIGINT(self, signum, frame):
        print()
        self.bot.trigger(lambda: self._kill(signum))

    def _kill(self, signum):
        if self._exited:
            return
        self._exited = True

        self.events.on("signal.interrupt").call(signum=signum)

        for server in self.bot.servers.values():
            reason = "Leaving"
            if server.get_setting("quit-quote", True):
                reason = self.events.on("get.quit-quote"
                    ).call_for_result(default=reason)
            server.send_quit(reason)

        self.events.on("writebuffer.empty").hook(
            lambda event: self.bot.disconnect(event["server"]))

    def SIGUSR1(self, signum, frame):
        self.bot.trigger(self._reload_config)

    def _reload_config(self):
        self.bot.log.info("Reloading config file", [])
        self.bot.config.load()
        self.bot.log.info("Reloaded config file", [])
