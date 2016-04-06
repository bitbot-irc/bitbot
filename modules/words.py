

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("new").on("server").hook(self.new_server)
        bot.events.on("received").on("message").on("channel"
            ).hook(self.channel_message)
        bot.events.on("received").on("command").on("words"
            ).hook(self.words, channel_only=True,
            usage="<nickname>")

    def new_server(self, event):
        event["server"].tracked_words = set([])
        settings = event["server"].find_settings("word-%")
        for word, _ in settings:
            word = word.split("word-", 1)[1]
            event["server"].tracked_words.add(word)

    def channel_message(self, event):
        words = list(filter(None, event["message_split"]))
        word_count = len(words)
        words = event["user"].get_setting("words", {})
        if not event["channel"].name in words:
            words[event["channel"].name] = 0
        words[event["channel"].name] += word_count
        event["user"].set_setting("words", words)
        for word in words:
            if word.lower() in event["server"].tracked_words:
                setting = "word-%s" % word
                tracked_word = event["server"].get_setting(setting, {})
                if not event["user"].name in tracked_word:
                    tracked_word[event["user"].name] = 0
                tracked_word[event["user"].name] += 1
                event["server"].set_setting(setting, tracked_word)

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
