import Utils

URL_WIKIPEDIA = "https://en.wikipedia.org/w/api.php"

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("command").on("wiki", "wi"
            ).hook(self.wikipedia, min_args=1)

    def wikipedia(self, event):
        page = Utils.get_url(URL_WIKIPEDIA, get_params={
            "action": "query", "prop": "extracts",
            "titles": event["args"], "exsentences": "2",
            "explaintext": "", "formatversion": "2",
            "format": "json"}, json=True)
        if page:
            if not "missing" in page["query"]["pages"][0]:
                article = page["query"]["pages"][0]
                title, info = article["title"], article["extract"]
                event["stdout"].write("%s: %s" % (title, info))
            else:
                event["stderr"].write("No results found")
        else:
            event["stderr"].write("Failed to load results")

