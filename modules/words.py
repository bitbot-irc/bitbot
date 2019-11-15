#--depends-on commands
#--depends-on config
#--depends-on permissions

import time
from src import EventManager, ModuleManager, utils

WORD_DELIM = "\"'…~*`"
WORD_START = WORD_DELIM+"“({<"
WORD_STOP = WORD_DELIM+"”)}>;:.,!?"

SETTING = utils.BoolSetting("word-tracking",
    "Disable/enable tracking your wordcounts")

@utils.export("set", SETTING)
@utils.export("channelset", SETTING)
class Module(ModuleManager.BaseModule):
    def _channel_message(self, user, event):
        if not event["channel"].get_setting("word-tracking", True
                ) or not user.get_setting("word-tracking", True):
            return

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
            stripped_word = word.lstrip(WORD_START).rstrip(WORD_STOP)
            found = None
            if word.lower() in tracked_words:
                found = word.lower()
            elif stripped_word.lower() in tracked_words:
                found = stripped_word.lower()

            if found:
                setting = "word-%s" % found
                word_count = user.get_setting(setting, 0)
                word_count += 1
                user.set_setting(setting, word_count)
    @utils.hook("received.message.channel",
        priority=EventManager.PRIORITY_MONITOR)
    def channel_message(self, event):
        self._channel_message(event["user"], event)
    @utils.hook("send.message.channel",
        priority=EventManager.PRIORITY_MONITOR)
    def self_channel_message(self, event):
        self._channel_message(event["server"].get_user(
            event["server"].nickname), event)

    @utils.hook("received.command.words", channel_only=True)
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

        since = ""
        first_words = target.get_setting("first-words", None)
        if not first_words == None:
            since = " since %s" % utils.date_human(
                utils.datetime_timestamp(first_words))

        event["stdout"].write("%s has used %d words (%d in %s)%s" % (
            target.nickname, total, this_channel, event["target"].name, since))

    @utils.hook("received.command.trackword", min_args=1)
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

    @utils.hook("received.command.trackedwords")
    def tracked_words(self, event):
        """
        :help: List which words are being tracked on the current network
        """
        event["stdout"].write("Tracked words: %s" % ", ".join(
            event["server"].get_setting("tracked-words", [])))

    @utils.hook("received.command.wordusers", min_args=1)
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
            top_10 = utils.top_10(word_users,
                convert_key=lambda nickname:
                event["server"].get_user(nickname).nickname)
            event["stdout"].write("Top '%s' users: %s" % (word,
                ", ".join(top_10)))
        else:
            event["stderr"].write("That word is not being tracked")

    @utils.hook("received.command.wordiest")
    def wordiest(self, event):
        """
        :help: Show wordiest users
        :usage: [channel]
        """
        channel_query = None
        word_prefix = ""
        if event["args_split"]:
            channel_query = event["args_split"][0].lower()
            word_prefix = " (%s)" % channel_query

        words = event["server"].find_all_user_channel_settings("words")
        user_words = {}
        for channel_name, nickname, word_count in words:
            if not channel_query or channel_name == channel_query:
                if not nickname in user_words:
                    user_words[nickname] = 0
                user_words[nickname] += word_count

        top_10 = utils.top_10(user_words,
            convert_key=lambda nickname:
            event["server"].get_user(nickname).nickname)
        event["stdout"].write("wordiest%s: %s" % (
            word_prefix, ", ".join(top_10)))
