import random
from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def on_load(self):
        if not self.bot.database.has_table("markov"):
            self.bot.database.execute("""CREATE TABLE markov
                (channel_id INTEGER, first_word TEXT, second_word TEXT,
                third_word TEXT, frequency INT,
                FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
                PRIMARY KEY (channel_id, first_word, second_word))""")

    @utils.hook("received.message.channel")
    def channel_message(self, event):
        words = event["message_split"]
        words_n = len(words)
        if words_n > 2 and event["channel"].get_setting("markov", False):

            inserts = []
            inserts.append([None, None, words[0]])
            inserts.append([None, words[0], words[1]])

            for i in range(words_n-2):
                inserts.append(words[i:i+3])

            inserts.append([words[-2], words[-1], None])
            inserts.append([words[-1], None, None])

            for insert in inserts:
                frequency = self.bot.database.execute("""SELECT frequency
                    FROM markov WHERE channel_id=? AND first_word=?
                    AND second_word=? AND third_word=?""",
                    [event["channel"].id]+insert)
                frequency = (frequency or [0])[0]+1

                self.bot.database.execute(
                    "INSERT OR REPLACE INTO markov VALUES (?, ?, ?, ?, ?)",
                    [event["channel"].id]+insert+[frequency])

    def _choose(self, words):
        words, frequencies = list(zip(*words))
        return random.choices(words, weights=frequencies, k=1)[0]

    @utils.hook("received.command.markov")
    @utils.kwarg("channel_only", True)
    def generate(self, event):
        if not event["target"].get_setting("markov", False):
            raise utils.EventError("Markov chains not enabled in this channel")
        out = self._generate(event["target"].id)
        if not out == None:
            event["stdout"].write(out)
        else:
            event["stderr"].write("Failed to generate markov chain")

    def _generate(self, channel_id):
        first_words = self.bot.database.execute_fetchall("""SELECT third_word,
            frequency FROM markov WHERE channel_id=? AND first_word IS NULL AND
            second_word IS NULL AND third_word NOT NULL""", [channel_id])
        if not first_words:
            return None
        first_word = self._choose(first_words)

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
