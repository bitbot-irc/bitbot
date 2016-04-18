

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("preprocess").on("command").hook(
            self.preprocess_command)

    def preprocess_command(self, event):
        if event["is_channel"] and event["hook"].kwargs.get(
                "require_mode"):
            required_mode = event["hook"].kwargs.get("require_mode")[0]
            if not event["target"].mode_or_above(event["user"].nickname,
                    required_mode):
                return "You do not have permission to do this"
