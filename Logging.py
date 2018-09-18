import logging, logging.handlers, sys, time

class BitBotFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            if "%f" in datefmt:
                msec = "%03d" % record.msecs
                datefmt = datefmt.replace("%f", msec)
            s = time.strftime(datefmt, ct)
        else:
            t = time.strftime("%Y-%m-%d %H:%M:%S", ct)
            s = "%s.%03d" % (t, record.msecs)
        return s

class Log(object):
    def __init__(self, bot):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        formatter = BitBotFormatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            "%Y-%m-%dT%H:%M:%S.%f%z")

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.INFO)
        stdout_handler.setFormatter(formatter)
        self.logger.addHandler(stdout_handler)

        file_handler = logging.handlers.TimedRotatingFileHandler(
            "bot.log", when="midnight", backupCount=5)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def debug(self, message, params, **kwargs):
        self._log(message, params, logging.DEBUG, kwargs)
    def info(self, message, params, **kwargs):
        self._log(message, params, logging.INFO, kwargs)
    def warn(self, message, params, **kwargs):
        self._log(message, params, logging.WARN, kwargs)
    def error(self, message, params, **kwargs):
        self._log(message, params, logging.ERROR, kwargs)
    def critical(self, message, params, **kwargs):
        self._log(message, params, logging.CRITICAL, kwargs)
    def _log(self, message, params, level, kwargs):
        self.logger.log(level, message, *params, **kwargs)
