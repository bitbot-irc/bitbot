import re
import Utils

URL_TRANSLATE = "https://translate.google.com/"
REGEX_LANGUAGES = re.compile("(\w{2})?:(\w{2})? ")

class Module(object):
    def __init__(self, bot):
        bot.events.on("received").on("command").on("translate", "tr").hook(
            self.translate, help="Translate the provided phrase or the "
            "last line seen.")

    def translate(self, event):
        phrase = event["args"]
        if not phrase:
            phrase = event["channel"].log.get()
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

        soup = Utils.get_url(URL_TRANSLATE, post_params={
            "sl": source_language, "tl": target_language, "js": "n",
            "prev": "_t", "hl": "en", "ie": "UTF-8", "text": phrase,
            "file": "", "edit-text": ""}, method="POST", soup=True)
        if soup:
            languages_element = soup.find(id="gt-otf-switch")
            translated_element = soup.find(id="result_box").find("span")
            if languages_element and translated_element:
                source_language, target_language = languages_element.attrs[
                    "href"].split("&sl=", 1)[1].split("&tl=", 1)
                target_language = target_language.split("&", 1)[0]
                translated = translated_element.text
                event["stdout"].write("(%s > %s) %s" % (source_language,
                    target_language, translated))
                return
        event["stderr"].write("Failed to translate, try checking "
            "source/target languages (https://cloud.google.com/translate/"
            "v2/using_rest#language-params")

