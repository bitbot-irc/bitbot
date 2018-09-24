from src import Utils

URL_WIKIPEDIA = "https://en.wikipedia.org/w/api.php"

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        events.on("received.command").on("wiki", "wi"
            ).hook(self.wikipedia, min_args=1)

    def wikipedia(self, event):
        page = Utils.get_url(URL_WIKIPEDIA, get_params={
            "action": "query", "prop": "extracts",
            "titles": event["args"], "exintro": "",
            "explaintext": "", "exchars": "500",
            "redirects": "", "format": "json"}, json=True)
        if page:
            pages = page["query"]["pages"]
            article = list(pages.items())[0][1]
            if not "missing" in article:
                title, info = article["title"], article["extract"]
                info = info.replace("\n\n", " ").split("\n")[0]
                event["stdout"].write("%s: %s" % (title, info))
            else:
                event["stderr"].write("No results found")
        else:
            event["stderr"].write("Failed to load results")

