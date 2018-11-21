import logging, logging.handlers, os, sys, time, typing

LEVELS = {
    "trace": logging.DEBUG-1,
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARN,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

class BitBotFormatter(logging.Formatter):
    converter = time.gmtime
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
    def __init__(self, level: str, location: str):
        logging.addLevelName(LEVELS["trace"], "TRACE")
        self.logger = logging.getLogger(__name__)

        if not level.lower() in LEVELS:
            raise ValueError("Unknown log level '%s'" % level)
        stdout_level = LEVELS[level.lower()]

        self.logger.setLevel(LEVELS["trace"])

        formatter = BitBotFormatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            "%Y-%m-%dT%H:%M:%S.%fZ")

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(stdout_level)
        stdout_handler.setFormatter(formatter)
        self.logger.addHandler(stdout_handler)

        file_handler = logging.handlers.TimedRotatingFileHandler(
            location, when="midnight", backupCount=5)
        file_handler.setLevel(LEVELS["trace"])
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def trace(self, message: str, params: typing.List, **kwargs):
        self._log(message, params, LEVELS["trace"], kwargs)
    def debug(self, message: str, params: typing.List, **kwargs):
        self._log(message, params, logging.DEBUG, kwargs)
    def info(self, message: str, params: typing.List, **kwargs):
        self._log(message, params, logging.INFO, kwargs)
    def warn(self, message: str, params: typing.List, **kwargs):
        self._log(message, params, logging.WARN, kwargs)
    def error(self, message: str, params: typing.List, **kwargs):
        self._log(message, params, logging.ERROR, kwargs)
    def critical(self, message: str, params: typing.List, **kwargs):
        self._log(message, params, logging.CRITICAL, kwargs)
    def _log(self, message: str, params: typing.List, level: int, kwargs: dict):
        self.logger.log(level, message, *params, **kwargs)
