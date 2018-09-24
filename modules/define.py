#--require-config wordnik-api-key

import Utils
import time

URL_WORDNIK = "https://api.wordnik.com/v4/word.json/%s/definitions"
URL_WORDNIK_RANDOM = "https://api.wordnik.com/v4/words.json/randomWord"

RANDOM_DELAY_SECONDS = 3

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        self.last_called = 0
        self.events = events

        events.on("received.command.define").hook(self.define,
            help="Define a provided term", usage="<phrase>")

        events.on("received.command.randomword").hook(self.random_word,
            help="Generate a random word!")

    def get_definition(self, event):
        word = event["args"] if "args" in event else event


        page = Utils.get_url(URL_WORDNIK % word, get_params={
            "useCanonical": "true", "limit": 1,
            "sourceDictionaries": "wiktionary", "api_key": self.bot.config[
                "wordnik-api-key"]}, json=True)

        return page

    def define(self, event):
        if event["args"]:
            word = event["args"]
        else:
            word = event["buffer"].get(from_self=False)
        page = self.get_definition(event)
        if page:
            if len(page):
                event["stdout"].write("%s: %s" % (page[0]["word"],
                    page[0]["text"]))
            else:
                event["stderr"].write("No definitions found")
        else:
            event["stderr"].write("Failed to load results")

    def random_word(self, event):
        if not self.last_called or (time.time()-self.last_called >=
                                    RANDOM_DELAY_SECONDS):

            self.last_called = time.time()

            page = Utils.get_url(URL_WORDNIK_RANDOM, get_params={
                "api_key":self.bot.config["wordnik-api-key"],
                "min_dictionary_count":1},json=True)
            if page:
                if len(page):
                    definition = self.get_definition(page["word"])

                    if len(definition):
                        definition = definition[0]
                    else:
                        self.events.on("send.stderr").call(module_name="Random",
                                       target=event["target"],
                                        message="Try again in a couple of seconds")
                        return

                    event["stdout"].set_prefix("Random")
                    event["stdout"].write("Random Word: %s - Definition: %s" % (
                        page["word"], definition["text"]))
                else:
                    event["stderr"].write("Something has gone terribly wrong")
            else:
                event["stderr"].write("Failed to load results")
        else:
            self.events.on("send.stderr").call(module_name="Random",
                          target=event["target"],
                          message="Try again in a couple of seconds")