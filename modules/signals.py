import signal
import Config

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        self.events = events
        signal.signal(signal.SIGINT, self.SIGINT)
        signal.signal(signal.SIGUSR1, self.SIGUSR1)

    def SIGINT(self, signum, frame):
        print()
        self.events.on("signal").on("interrupt").call(signum=signum,
            frame=frame)

        for server in self.bot.servers.values():
            reason = "Leaving"
            if server.get_setting("quit-quote", True):
                reason = self.events.on("get.quit-quote"
                    ).call_for_result(default="Leaving")
            server.send_quit(reason)
            self.bot.register_write(server)

        self.bot.running = False

    def SIGUSR1(self, signum, frame):
        self.bot.log.info("Reloading config file", [])
        config = Config.Config(self.bot, self.bot.args.config)
        self.bot.config = config.load_config()
        self.bot.log.info("Reloaded config file", [])
