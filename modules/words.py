

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("message").on("channel"
            ).hook(self.channel_message)
        bot.events.on("received").on("command").on("words"
            ).hook(self.words, channel_only=True)

    def channel_message(self, event):
        word_count = len(list(filter(None, event["message_split"
            ])))
        words = event["user"].get_setting("words", {})
        if not event["channel"].name in words:
            words[event["channel"].name] = 0
        words[event["channel"].name] += word_count
        event["user"].set_setting("words", words)

    def words(self, event):
        if event["args_split"]:
            target = event["server"].get_user(event["args_split"
                ][0])
        else:
            target = event["user"]
        words = target.get_setting("words", {})
        this_channel = words.get(event["target"].name, 0)
        total = 0
        for channel in words:
            total += words[channel]
        event["stdout"].write("%s has used %d words (%d in %s)" % (
            target.nickname, total, this_channel, event["target"].name))
