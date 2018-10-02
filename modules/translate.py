import json, re
from src import ModuleManager, Utils

URL_TRANSLATE = "http://translate.googleapis.com/translate_a/single"
URL_LANGUAGES = "https://cloud.google.com/translate/docs/languages"
REGEX_LANGUAGES = re.compile("(\w+)?:(\w+)? ")

class Module(ModuleManager.BaseModule):
    @Utils.hook("received.command.translate|tr")
    def translate(self, event):
        """
        :help: Translate the provided phrase or the last line in thie current
            channel
        :usage: [phrase]
        """
        phrase = event["args"]
        if not phrase:
            phrase = event["target"].buffer.get()
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

