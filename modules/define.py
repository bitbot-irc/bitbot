#--depends-on commands
#--require-config wordnik-api-key

import time
from src import ModuleManager, utils

URL_WORDNIK = "https://api.wordnik.com/v4/word.json/%s/definitions"
URL_WORDNIK_RANDOM = "https://api.wordnik.com/v4/words.json/randomWord"

RANDOM_DELAY_SECONDS = 3

class Module(ModuleManager.BaseModule):
    _last_called = 0

    def _get_definition(self, word):
        page = utils.http.request(URL_WORDNIK % word, get_params={
            "useCanonical": "true", "limit": 1,
            "sourceDictionaries": "wiktionary",
            "api_key": self.bot.config["wordnik-api-key"]})

        if page:
            if page.code == 200:
                return True, page.json()[0]
            else:
                return True, None
        else:
            return False, None

    @utils.hook("received.command.define")
    def define(self, event):
        """
        :help: Define a provided term
        :usage: <phrase>
        """
        if event["args"]:
            word = event["args"]
        else:
            word = event["target"].buffer.get(from_self=False)
        word = word.replace(" ", "+")

        success, definition = self._get_definition(word)
        if success:
            if not definition == None:
                text = utils.http.strip_html(definition["text"])
                event["stdout"].write("%s: %s" % (definition["word"], text))
            else:
                event["stderr"].write("No definitions found")
        else:
            raise utils.EventResultsError()

    @utils.hook("received.command.randomword")
    def random_word(self, event):
        """
        :help: Define a random word
        """
        if not self._last_called or (time.time()-self._last_called >=
                RANDOM_DELAY_SECONDS):
            self._last_called = time.time()

            page = utils.http.request(URL_WORDNIK_RANDOM, get_params={
                "api_key": self.bot.config["wordnik-api-key"],
                "min_dictionary_count": 1}).json()
            if page:
                success, definition = self._get_definition(page["word"])
                if not success:
                    raise utils.EventError("Try again in a couple of seconds")

                text = utils.http.strip_html(definition["text"])
                event["stdout"].write("Random Word: %s - Definition: %s" % (
                    page["word"], text))
            else:
                raise utils.EventResultsError()
        else:
            event["stderr"].write("Try again in a couple of seconds")
