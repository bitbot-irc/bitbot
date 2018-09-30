#--require-config wordnik-api-key

import time
from src import ModuleManager, Utils

URL_WORDNIK = "https://api.wordnik.com/v4/word.json/%s/definitions"
URL_WORDNIK_RANDOM = "https://api.wordnik.com/v4/words.json/randomWord"

RANDOM_DELAY_SECONDS = 3

class Module(ModuleManager.BaseModule):
    _last_called = 0

    def _get_definition(self, word):
        page = Utils.get_url(URL_WORDNIK % word, get_params={
            "useCanonical": "true", "limit": 1,
            "sourceDictionaries": "wiktionary", "api_key": self.bot.config[
            "wordnik-api-key"]}, json=True)

        return page

    @Utils.hook("received.command.define", usage="<phrase>")
    def define(self, event):
        """
        Define a provided term
        """
        if event["args"]:
            word = event["args"]
        else:
            word = event["target"].buffer.get(from_self=False)

        page = self._get_definition(word)
        if page:
            if len(page):
                event["stdout"].write("%s: %s" % (page[0]["word"],
                    page[0]["text"]))
            else:
                event["stderr"].write("No definitions found")
        else:
            event["stderr"].write("Failed to load results")

    @Utils.hook("received.command.randomword")
    def random_word(self, event):
        """
        Define a random word
        """
        if not self._last_called or (time.time()-self._last_called >=
                RANDOM_DELAY_SECONDS):
            self._last_called = time.time()

            page = Utils.get_url(URL_WORDNIK_RANDOM, get_params={
                "api_key":self.bot.config["wordnik-api-key"],
                "min_dictionary_count":1},json=True)
            if page and len(page):
                definition = self._get_definition(page["word"])
                if len(definition):
                    definition = definition[0]
                else:
                    event["stderr"].write("Try again in a couple of "
                        "seconds")
                    return
                event["stdout"].write("Random Word: %s - Definition: %s" % (
                    page["word"], definition["text"]))
            else:
                event["stderr"].write("Failed to load results")
        else:
            event["stderr"].write("Try again in a couple of seconds")
