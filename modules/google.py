#--depends-on commands
#--depends-on config
#--require-config google-api-key
#--require-config google-search-id

import json
from src import ModuleManager, utils

URL_GOOGLESEARCH = "https://www.googleapis.com/customsearch/v1"
URL_GOOGLESUGGEST = "http://google.com/complete/search"

@utils.export("channelset", utils.BoolSetting("google-safesearch",
    "Turn safe search off/on"))
class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.g", alias_of="google")
    @utils.hook("received.command.google")
    def google(self, event):
        """
        :help: Get first Google result for a given search term
        :usage: [search term]
        """

        phrase = event["args"] or event["target"].buffer.get()
        if phrase:
            safe_setting = event["target"].get_setting("google-safesearch",
                True)
            safe = "active" if safe_setting else "off"

            page = utils.http.request(URL_GOOGLESEARCH, get_params={
                "q": phrase, "prettyPrint": "true", "num": 1, "gl": "gb",
                "key": self.bot.config["google-api-key"],
                "cx": self.bot.config["google-search-id"],
                "safe": safe}).json()
            if page:
                if "items" in page and len(page["items"]):
                    item = page["items"][0]
                    link = item["link"]
                    text = utils.parse.line_normalise(
                        item["snippet"] or item["title"])
                    event["stdout"].write(
                        "%s: %s - %s" % (event["user"].nickname, text, link))
                else:
                    event["stderr"].write("No results found")
            else:
                raise utils.EventResultsError()
        else:
            event["stderr"].write("No phrase provided")

    @utils.hook("received.command.suggest")
    def suggest(self, event):
        """
        :help: Get suggested phrases from Google
        :usage: [phrase]
        """
        phrase = event["args"] or event["target"].buffer.get()
        if phrase:
            page = utils.http.request(URL_GOOGLESUGGEST, get_params={
                "output": "json", "client": "hp", "gl": "gb", "q": phrase}
                ).json()
            if page:
                # google gives us jsonp, so we need to unwrap it.
                page = page.split("(", 1)[1][:-1]
                page = json.loads(page)
                suggestions = page[1]
                suggestions = [utils.http.strip_html(s[0]) for s in suggestions]

                if suggestions:
                    event["stdout"].write("%s: %s" % (phrase,
                        ", ".join(suggestions)))
                else:
                    event["stderr"].write("No suggestions found")
            else:
                raise utils.EventResultsError()
        else:
            event["stderr"].write("No phrase provided")
