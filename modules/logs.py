import datetime

class Module(object):
    def __init__(self, bot):
        bot.events.on("log").on("info", "warn", "error").hook(self.log)

    def timestamp(self):
        return datetime.datetime.utcnow().isoformat()+"Z"

    def log(self, event):
        log_level = event.name
        timestamp = self.timestamp()
        message = event["message"]
        data = event.get("data")
        with open("bot.log", "a") as log_file:
            log_file.write("%s [%s] %s\n" % (timestamp, log_level,
                message))
            if data:
                log_file.write("%s\n" % data)
