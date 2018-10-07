import signal
from src import Config, utils

@utils.export("serverset", {"setting": "quit-quote",
    "help": "Set whether I pick a random quote to /quit with",
    "validate": utils.bool_or_none})
class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        self.events = events
        signal.signal(signal.SIGINT, self.SIGINT)
        signal.signal(signal.SIGUSR1, self.SIGUSR1)

    def SIGINT(self, signum, frame):
        print()
        self.events.on("signal.interrupt").call(signum=signum, frame=frame)

        for server in self.bot.servers.values():
            reason = "Leaving"
            if server.get_setting("quit-quote", True):
                reason = self.events.on("get.quit-quote"
                    ).call_for_result(default=reason)
            server.send_quit(reason)
            self.bot.trigger()

        self.bot.running = False

    def SIGUSR1(self, signum, frame):
        self.bot.log.info("Reloading config file", [])
        self.bot.config.load()
        self.bot.log.info("Reloaded config file", [])
