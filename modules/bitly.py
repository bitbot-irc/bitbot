# --require-config bitly-api-key

import re
import Utils

URL_BITLYSHORTEN = "https://api-ssl.bitly.com/v3/shorten"
REGEX_URL = re.compile("https?://", re.I)


class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("get").on("shortlink").hook(self.shortlink)
        bot.events.on("received").on("command").on("shorten"
                                                   ).hook(self.shorten,
                                                          min_args=1,
                                                          help="Shorten a URL.",
                                                          usage="<url>")

    def shortlink(self, event):
        url = event["url"]
        if not re.match(REGEX_URL, url):
            url = "http://%s" % url
        data = Utils.get_url(URL_BITLYSHORTEN, get_params={
            "access_token": self.bot.config["bitly-api-key"],
            "longUrl": url}, json=True)
        if data and data["data"]:
            return data["data"]["url"]

    def shorten(self, event):
        link = self.bot.events.on("get").on("shortlink"
                                            ).call_for_result(url=event["args"])
        if link:
            event["stdout"].write("Short URL: %s" % link)
        else:
            event["stderr"].write("Unable to shorten that URL.")
