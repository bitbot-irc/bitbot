import re
from src import Utils

ISGD_API_URL = "https://is.gd/create.php"
REGEX_URL = re.compile("https?://", re.I)

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        self.events = events
        events.on("get.shortlink").hook(self.shortlink)
        events.on("received.command.shorten").hook(self.shorten, min_args=1,
            help="Shorten a URL using the is.gd service.", usage="<url>")

    def shortlink(self, event):
        url = event["url"]
        if not re.match(REGEX_URL, url):
            url = "http://%s" % url
        data = Utils.get_url(ISGD_API_URL, get_params={
            "format": "json",
            "url": url
        }, json=True)

        if data and data["shorturl"]:
            return data["shorturl"]

    def shorten(self, event):
        link = self.events.on("get.shortlink").call_for_result(
            url=event["args"])
        if link:
            event["stdout"].write("Shortened URL: %s" % link)
        else:
            event["stderr"].write("Unable to shorten that URL.")
