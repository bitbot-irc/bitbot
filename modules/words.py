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
REGISTERED_SETTING = utils.BoolSetting("word-tracking-registered",
    "Whether or not word tracking is registered-users-only")

@utils.export("set", SETTING)
@utils.export("channelset", SETTING)
@utils.export("serverset", REGISTERED_SETTING)
@utils.export("channelset", REGISTERED_SETTING)
@utils.export("channelset", utils.BoolSetting("words-prevent-highlight",
    "Whether or not to prevent highlights in wordiest lists"))
class Module(ModuleManager.BaseModule):
    def on_load(self):
        if not self.bot.database.has_table("words"):
            self.bot.database.execute("""CREATE TABLE words
                (user_id INTEGER, channel_id INTEGER, date TEXT, count INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
                PRIMARY KEY (user_id, channel_id, date))""")

    def _get_words_date(self, user, channel, date):
        words = self.bot.database.execute_fetchone("""SELECT count FROM words
            WHERE user_id=? AND channel_id=? AND date=?""",
            [user.get_id(), channel.id, date])
        return (words or [0])[0]
    def _set_words_date(self, user, channel, date, count):
        self.bot.database.execute("""
            INSERT OR REPLACE INTO words (user_id, channel_id, date, count)
            VALUES (?, ?, ?, ?)""", [user.get_id(), channel.id, date, count])

    def _channel_between_dates(self, channel, date1, date2):
        return self.bot.database.execute_fetchall("""
            SELECT user_id, count FROM words
            WHERE channel_id=? AND date>=? AND date<=?""",
            [channel.id, date1, date2])
    def _channel_all(self, channel):
        return self.bot.database.execute_fetchall(
            "SELECT user_id, count FROM words WHERE channel_id=?",
            [channel.id])

    def _user_between_dates(self, user, channel, date1, date2):
        return self.bot.datebase.execute_fetchall("""
            SELECT count FROM words
            WHERE user_id=? AND channel_id=? AND date>=? AND date<=?""",
            [user.get_id(), channel.id, date1, date2])
    def _user_all(self, user):
        return self.bot.database.execute_fetchall(
            "SELECT channel_id, count FROM words WHERE user_id=?",
            [user.get_id()])

    def _channel_message(self, user, event):
        if not event["channel"].get_setting("word-tracking", True
                ) or not user.get_setting("word-tracking", True):
            return

        if event["channel"].get_setting("word-tracking-registered",
                event["server"].get_setting("word-tracking-registered", False)):
            if not self.exports.get("is-identified")(event["user"]):
                return

        if user.get_setting("first-words", None) == None:
            user.set_setting("first-words", time.time())

        words = list(filter(None, event["message_split"]))
        word_count = len(words)

        date = utils.datetime.format.date_human(utils.datetime.utcnow())
        user_words = self._get_words_date(event["user"], event["channel"], date)
        self._set_words_date(event["user"], event["channel"], date,
            user_words+word_count)

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

    @utils.hook("received.command.words")
    @utils.kwarg("help",
        "See how many words you or the given nickname have used")
    @utils.spec("?<nickname>ouser")
    def words(self, event):
        if event["spec"][0] and event["is_channel"]:
            target_user = event["spec"][0]
        else:
            target_user = event["user"]

        word_items = self._user_all(target_user)

        words = {}
        for channel_id, count in word_items:
            if not channel_id in words:
                words[channel_id] = 0
            words[channel_id] += count
        total = sum(words.values())

        since = ""
        first_words = target_user.get_setting("first-words", None)
        if not first_words == None:
            since = " since %s" % utils.datetime.format.date_human(
                utils.datetime.timestamp(first_words))

        if event["is_channel"]:
            this_channel = words.get(event["target"].id, 0)
            event["stdout"].write("%s has used %d words (%d in %s)%s" % (
                target_user.nickname, total, this_channel, event["target"].name,
                since))
        else:
            event["stdout"].write("%s has used %d words%s" % (
                target_user.nickname, total, since))

    @utils.hook("received.command.trackword")
    @utils.kwarg("help", "Start tracking a word")
    @utils.kwarg("permission", "track-word")
    @utils.spec("!<word>wordlower")
    def track_word(self, event):
        word = event["args_split"][0].lower()
        tracked_words = event["server"].get_setting("tracked-words", [])
        if not word in tracked_words:
            tracked_words.append(word)
            event["server"].set_setting("tracked-words", tracked_words)
            event["stdout"].write("Now tracking '%s'" % word)
        else:
            event["stderr"].write("Already tracking '%s'" % word)

    @utils.hook("received.command.trackedwords")
    @utils.kwarg("help",
        "List which words are being tracked on the current network")
    def tracked_words(self, event):
        event["stdout"].write("Tracked words: %s" % ", ".join(
            event["server"].get_setting("tracked-words", [])))

    def _get_nickname(self, server, target, nickname):
        nickname = server.get_user(nickname).nickname
        if target.get_setting("words-prevent-highlight", True):
            nickname = utils.prevent_highlight(nickname)
        return nickname

    @utils.hook("received.command.wordusers")
    @utils.kwarg("help", "Show who has used a tracked word the most")
    @utils.spec("!<word>wordlower")
    def word_users(self, event):
        word = event["args_split"][0].lower()
        if word in event["server"].get_setting("tracked-words", []):
            word_users = event["server"].get_all_user_settings(
                "word-%s" % word, [])
            items = [(word_user[0], word_user[1]) for word_user in word_users]
            word_users = dict(items)
            top_10 = utils.top_10(word_users,
                convert_key=lambda nickname: self._get_nickname(
                event["server"], event["target"], nickname))
            event["stdout"].write("Top '%s' users: %s" % (word,
                ", ".join(top_10)))
        else:
            event["stderr"].write("That word is not being tracked")

    @utils.hook("received.command.wordiest")
    @utils.kwarg("help", "Show wordiest users")
    @utils.spec("!-channelonly ?<start>date ?<end>date")
    def wordiest(self, event):
        date_str = ""

        if event["spec"][0]:
            date1 = utils.datetime.format.date_human(event["spec"][0])
            date2 = utils.datetime.format.date_human(
                event["spec"][1] or utils.datetime.utcnow())

            date_str = f" ({date1} to {date2})"
            words = self._channel_between_dates(event["target"], date1, date2)
        else:
            words = self._channel_all(event["target"])

        user_words = {}
        for user_id, word_count in words:
            _, nickname = self.bot.database.users.by_id(user_id)
            if not nickname in user_words:
                user_words[nickname] = 0
            user_words[nickname] += word_count

        top_10 = utils.top_10(user_words,
            convert_key=lambda nickname: self._get_nickname(
            event["server"], event["target"], nickname))
        event["stdout"].write("wordiest in %s%s: %s" %
            (str(event["target"]), date_str, ", ".join(top_10)))
