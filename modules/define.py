#--require-config wordnik-api-key

import Utils

URL_WORDNIK = "http://api.wordnik.com:80/v4/word.json/%s/definitions"

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("command").on("define").hook(
            self.define, help="Define a provided term",
            usage="<phrase>")

    def define(self, event):
        if event["args"]:
            word = event["args"]
        else:
            word = event["log"].get(from_self=False)
        page = Utils.get_url(URL_WORDNIK % event["args"], get_params={
            "useCanonical": "true", "limit": 1,
            "sourceDictionaries": "wiktionary", "api_key": self.bot.config[
                "wordnik-api-key"]}, json=True)
        if page:
            if len(page):
                event["stdout"].write("%s: %s" % (page[0]["word"],
                    page[0]["text"]))
            else:
                event["stderr"].write("No definitions found")
        else:
            event["stderr"].write("Failed to load results")
