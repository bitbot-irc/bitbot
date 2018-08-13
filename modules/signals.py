import signal

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        signal.signal(signal.SIGINT, self.SIGINT)
        signal.signal(signal.SIGUSR1, self.SIGUSR1)

    def SIGINT(self, signum, frame):
        print()
        self.bot.events.on("signal").on("interrupt").call(signum=signum, frame=frame)

        for server in self.bot.servers.values():
            reason = "Leaving"
            if server.get_setting("quit-quote", True):
                reason = self.bot.events.on("get.quit-quote"
                    ).call_for_result(default="Leaving")
            server.send_quit(reason)
            self.bot.register_write(server)

        self.bot.running = False

    def SIGUSR1(self, signum, frame):
        print("Reloading config file")
        self.bot.config_object.load_config()
