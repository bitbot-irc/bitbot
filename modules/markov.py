import random, threading
from src import ModuleManager, utils

NO_MARKOV = "Markov chains not enabled in this channel"

class Module(ModuleManager.BaseModule):
    _load_thread = None

    def on_load(self):
        if not self.bot.database.has_table("markov"):
            self.bot.database.execute("""CREATE TABLE markov
                (channel_id INTEGER, first_word TEXT, second_word TEXT,
                third_word TEXT, frequency INT,
                FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
                PRIMARY KEY (channel_id, first_word, second_word))""")

    @utils.hook("received.message.channel")
    def channel_message(self, event):
        if event["channel"].get_setting("markov", False):
            self._create(event["channel"].id, event["message_split"])

    @utils.hook("received.command.markovlog")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("permission", "markovlog")
    @utils.kwarg("help", "Load a message-only newline-delimited log in to this "
        "channel's markov chain")
    def load_log(self, event):
        if not event["target"].get_setting("markov", False):
            raise utils.EventError(NO_MARKOV)

        if not self._load_thread == None:
            raise utils.EventError("Log loading already in progress")

        page = utils.http.request(event["args_split"][0])
        if page.code == 200:
            event["stdout"].write("Importing...")
            self._load_thread = threading.Thread(target=self._load_loop,
                args=[event["target"].id, page.data])
            self._load_thread.daemon = True
            self._load_thread.start()
        else:
            event["stderr"].write("Failed to load log (%d)" % page.code)

    def _load_loop(self, channel_id, data):
        for line in data.decode("utf8").split("\n"):
            line = line.strip("\r").split(" ")
            self.bot.trigger(self._create_factory(channel_id, line))
        self._load_thread = None
    def _create_factory(self, channel_id, line):
        return lambda: self._create(channel_id, line)

    def _create(self, channel_id, words):
        words = list(filter(None, words))
        words = [word.lower() for word in words]
        words_n = len(words)

        if not words_n > 2:
            return

        inserts = []
        inserts.append([None, None, words[0]])
        inserts.append([None, words[0], words[1]])

        for i in range(words_n-2):
            inserts.append(words[i:i+3])

        inserts.append([words[-2], words[-1], None])

        for insert in inserts:
            frequency = self.bot.database.execute_fetchone("""SELECT
                frequency FROM markov WHERE channel_id=? AND first_word=?
                AND second_word=? AND third_word=?""",
                [channel_id]+insert)
            frequency = (frequency or [0])[0]+1

            self.bot.database.execute(
                "INSERT OR REPLACE INTO markov VALUES (?, ?, ?, ?, ?)",
                [channel_id]+insert+[frequency])

    def _choose(self, words):
        words, frequencies = list(zip(*words))
        return random.choices(words, weights=frequencies, k=1)[0]

    @utils.hook("received.command.markov")
    @utils.kwarg("channel_only", True)
    @utils.kwarg("help", "Generate a markov chain for the current channel")
    def markov(self, event):
        self._markov_for(event["target"], event["stdout"], event["stderr"],
            first_word=(event["args_split"] or [None])[0])

    @utils.hook("received.command.markovfor")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("permission", "markovfor")
    @utils.kwarg("help", "Generate a markov chain for a given channel")
    @utils.kwarg("usage", "<channel>")
    def markov_for(self, event):
        if event["args_split"][0] in event["server"].channels:
            channel = event["server"].channels.get(event["args_split"][0])
            self._markov_for(channel, event["stdout"], event["stderr"])
        else:
            event["stderr"].write("Unknown channel")

    def _markov_for(self, channel, stdout, stderr, first_word=None):
        if not channel.get_setting("markov", False):
            stderr.write(NO_MARKOV)
        else:
            out = self._generate(channel.id, first_word)
            if not out == None:
                stdout.write(out)
            else:
                stderr.write("Failed to generate markov chain")

    def _generate(self, channel_id, first_word):
        if start == None:
            first_words = self.bot.database.execute_fetchall("""SELECT
                third_word, frequency FROM markov WHERE channel_id=? AND
                first_word IS NULL AND second_word IS NULL AND third_word
                NOT NULL""", [channel_id])
            if not first_words:
                return None
            first_word = self._choose(first_words)
        else:
            first_word = first_word.lower()

        second_words = self.bot.database.execute_fetchall("""SELECT third_word,
            frequency FROM markov WHERE channel_id=? AND first_word IS NULL AND
            second_word=? AND third_word NOT NULL""", [channel_id, first_word])
        if not second_words:
            return None
        second_word = self._choose(second_words)

        words = [first_word, second_word]
        for i in range(30):
            two_words = words[-2:]
            third_words = self.bot.database.execute_fetchall("""SELECT
                third_word, frequency FROM markov WHERE channel_id=? AND
                first_word=? AND second_word=?""", [channel_id]+two_words)

            third_word = self._choose(third_words)
            if third_word == None:
                break
            words.append(third_word)

        return " ".join(words)
