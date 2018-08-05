import logging, sys

class Module(object):
    def __init__(self, bot):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            "%Y-%m-%dT%H:%M:%S%z")

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.INFO)
        stdout_handler.setFormatter(formatter)
        self.logger.addHandler(stdout_handler)

        file_handler = logging.FileHandler('bot.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        bot.events.on("log.debug").hook(self.debug)
        bot.events.on("log.info").hook(self.info)
        bot.events.on("log.warn").hook(self.warn)
        bot.events.on("log.error").hook(self.error)
        bot.events.on("log.critical").hook(self.critical)

    def debug(self, event):
        self._log(event, logging.DEBUG)
    def info(self, event):
        self._log(event, logging.INFO)
    def warn(self, event):
        self._log(event, logging.WARN)
    def error(self, event):
        self._log(event, logging.ERROR)
    def critical(self, event):
        self._log(event, logging.CRITICAL)
    def _log(self, event, level):
        message = event["message"]
        params = event.get("params", [])
        self.logger.log(level, message, *params)
