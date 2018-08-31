#--require-config google-api-key
#--require-config google-search-id

import Utils

URL_GOOGLESEARCH = "https://www.googleapis.com/customsearch/v1"

class Module(object):
    def __init__(self, bot, events):
        self.bot = bot
        events.on("received").on("command").on("google",
            "g").hook(self.google, help="Google feeling lucky",
            usage="[search term]")

    def google(self, event):
        phrase = event["args"] or event["buffer"].get()
        if phrase:
            page = Utils.get_url(URL_GOOGLESEARCH, get_params={
                "q": phrase, "key": self.bot.config[
                "google-api-key"], "cx": self.bot.config[
                "google-search-id"], "prettyPrint": "true",
                "num": 1, "gl": "gb"}, json=True)
            if page:
                if "items" in page and len(page["items"]):
                    event["stdout"].write(page["items"][0][
                        "link"])
                else:
                    event["stderr"].write("No results found")
            else:
                event["stderr"].write("Failed to load results")
        else:
            event["stderr"].write("No phrase provided")
