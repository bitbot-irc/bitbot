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
            "sourceDictionaries": "wiktionary", "api_key": self.bot.config[
            "wordnik-api-key"]}, json=True)

        return page

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

        page = self._get_definition(word)
        if page:
            if len(page.data):
                event["stdout"].write("%s: %s" % (page.data[0]["word"],
                    page.data[0]["text"]))
            else:
                event["stderr"].write("No definitions found")
        else:
            raise utils.EventsResultsError()

    @utils.hook("received.command.randomword")
    def random_word(self, event):
        """
        :help: Define a random word
        """
        if not self._last_called or (time.time()-self._last_called >=
                RANDOM_DELAY_SECONDS):
            self._last_called = time.time()

            page = utils.http.request(URL_WORDNIK_RANDOM, get_params={
                "api_key":self.bot.config["wordnik-api-key"],
                "min_dictionary_count":1},json=True)
            if page and len(page.data):
                definition = self._get_definition(page.data["word"])
                if definition and len(definition.data):
                    definition = definition.data[0]
                else:
                    raise utils.EventError("Try again in a couple of seconds")

                event["stdout"].write("Random Word: %s - Definition: %s" % (
                    page.data["word"], definition["text"]))
            else:
                raise utils.EventsResultsError()
        else:
            event["stderr"].write("Try again in a couple of seconds")
