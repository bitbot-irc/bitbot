#--depends-on commands
#--require-config google-api-key

import json, re
from src import ModuleManager, utils

URL_TRANSLATE = "https://translation.googleapis.com/language/translate/v2"
URL_LANGUAGES = "https://cloud.google.com/translate/docs/languages"
REGEX_LANGUAGES = re.compile("(\w+)?:(\w+)? ")


class Module(ModuleManager.BaseModule):

    @utils.hook("received.command.tr", alias_of="translate")
    @utils.hook("received.command.translate")
    @utils.spec("?<from:to>lstring !<phrase>lstring")
    def translate(self, event):
        """
        :help: Translate the provided phrase or the last line in thie current
            channel
        :usage: [phrase]
        """
        phrase = event["spec"][0]
        source_language = "auto"
        target_language = "en"

        language_match = re.match(REGEX_LANGUAGES, phrase)
        if language_match:
            if language_match.group(1):
                source_language = language_match.group(1)
            if language_match.group(2):
                target_language = language_match.group(2)
            phrase = phrase.split(" ", 1)[1]

        page = utils.http.request(URL_TRANSLATE,
                                  method="POST",
                                  post_data={
                                      "q": phrase,
                                      "format": "text",
                                      "source": source_language,
                                      "target": target_language,
                                      "key": self.bot.config["google-api-key"]
                                  }).json()

        if "data" in page:
            translation = page["data"]["translations"][0]["translatedText"]
            event["stdout"].write("(%s -> %s) %s" % (source_language, target_language, translation))
        else:
            event["stderr"].write("Failed to translate, try checking "
                                  "source/target languages (" + URL_LANGUAGES + ")")
