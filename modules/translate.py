import json, re
import Utils

URL_TRANSLATE = "http://translate.googleapis.com/translate_a/single"
URL_LANGUAGES = "https://cloud.google.com/translate/docs/languages"
REGEX_LANGUAGES = re.compile("(\w{2})?:(\w{2})? ")

class Module(object):
    def __init__(self, bot):
        bot.events.on("received").on("command").on("translate", "tr").hook(
            self.translate, help="Translate the provided phrase or the "
            "last line seen.", usage="[phrase]")

    def translate(self, event):
        phrase = event["args"]
        if not phrase:
            phrase = event["log"].get()
            if phrase:
                phrase = phrase.message
        if not phrase:
            event["stderr"].write("No phrase provided.")
            return
        source_language = "auto"
        target_language = "en"

        language_match = re.match(REGEX_LANGUAGES, phrase)
        if language_match:
            if language_match.group(1):
                source_language = language_match.group(1)
            if language_match.group(2):
                target_language = language_match.group(2)
            phrase = phrase.split(" ", 1)[1]

        data = Utils.get_url(URL_TRANSLATE, get_params={
            "client": "gtx", "sl": source_language,
            "tl": target_language, "dt": "t", "q": phrase})

        if data and not data == "[null,null,\"\"]":
            while ",," in data:
                data = data.replace(",,", ",null,")
                data = data.replace("[,", "[null,")
            data_json = json.loads(data)
            detected_source = data_json[2]
            event["stdout"].write("(%s -> %s) %s" % (
                detected_source, target_language.lower(),
                data_json[0][0][0]))
        else:
            event["stderr"].write("Failed to translate, try checking "
                "source/target languages (" + URL_LANGUAGES + ")")

