import time
from src import ModuleManager, Utils

class Module(ModuleManager.BaseModule):
    def _channel_message(self, user, event):
        words = list(filter(None, event["message_split"]))
        word_count = len(words)

        user_words = event["channel"].get_user_setting(user.get_id(),
            "words", 0)
        user_words += word_count

        if user.get_setting("first-words", None) == None:
            user.set_setting("first-words", time.time())

        event["channel"].set_user_setting(user.get_id(), "words", user_words)

        tracked_words = set(event["server"].get_setting(
            "tracked-words", []))
        for word in words:
            if word.lower() in tracked_words:
                setting = "word-%s" % word
                word_count = user.get_setting(setting, 0)
                word_count += 1
                user.set_setting(setting, word_count)
    @Utils.hook("received.message.channel")
    def channel_message(self, event):
        self._channel_message(event["user"], event)
    @Utils.hook("self.message.channel")
    def self_channel_message(self, event):
        self._channel_message(event["server"].get_user(
            event["server"].nickname), event)

    @Utils.hook("received.command.words", channel_only=True)
    def words(self, event):
        """
        :help: See how many words you or the given nickname have used
        :usage: [nickname]
        """
        if event["args_split"]:
            target = event["server"].get_user(event["args_split"
                ][0])
        else:
            target = event["user"]
        words = dict(target.get_channel_settings_per_setting(
            "words", []))
        this_channel = words.get(event["target"].name, 0)

        total = 0
        for channel in words:
            total += words[channel]
        event["stdout"].write("%s has used %d words (%d in %s)" % (
            target.nickname, total, this_channel, event["target"].name))

    @Utils.hook("received.command.trackword", min_args=1)
    def track_word(self, event):
        """
        :help: Start tracking a word
        :usage: <word>
        :permission: track-word
        """
        word = event["args_split"][0].lower()
        tracked_words = event["server"].get_setting("tracked-words", [])
        if not word in tracked_words:
            tracked_words.append(word)
            event["server"].set_setting("tracked-words", tracked_words)
            event["stdout"].write("Now tracking '%s'" % word)
        else:
            event["stderr"].write("Already tracking '%s'" % word)

    @Utils.hook("received.command.wordusers", min_args=1)
    def word_users(self, event):
        """
        :help: Show who has used a tracked word the most
        :usage: <word>
        """
        word = event["args_split"][0].lower()
        if word in event["server"].get_setting("tracked-words", []):
            word_users = event["server"].get_all_user_settings(
                "word-%s" % word, [])
            items = [(word_user[0], word_user[1]) for word_user in word_users]
            word_users = dict(items)

            top_10 = sorted(word_users.keys())
            top_10 = sorted(top_10, key=word_users.get, reverse=True)[:10]
            top_10 = ", ".join("%s (%d)" % (Utils.prevent_highlight(event[
                "server"].get_user(nickname).nickname), word_users[nickname]
                ) for nickname in top_10)
            event["stdout"].write("Top '%s' users: %s" % (word, top_10))
        else:
            event["stderr"].write("That word is not being tracked")
