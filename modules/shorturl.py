#--require-config bitly-api-key

import re
from src import ModuleManager, utils

URL_BITLYSHORTEN = "https://api-ssl.bitly.com/v3/shorten"

class Module(ModuleManager.BaseModule):
    _name = "Short"

    def on_load(self):
        self.exports.add("shortlink", self._shortlink)

    def _shortlink(self, url):
        if not re.match(utils.http.REGEX_URL, url):
            url = "http://%s" % url

        page = utils.http.request(URL_BITLYSHORTEN, get_params={
            "access_token": self.bot.config["bitly-api-key"],
            "longUrl": url}, json=True)

        if page and page.data["data"]:
            return page.data["data"]["url"]

    @utils.hook("received.command.shorten")
    def shorten(self, event):
        """
        :help: Shorten a given URL using the is.gd service
        :usage: <url>
        """
        url = None
        if len(event["args"]) > 0:
            url = event["args_split"][0]
        else:
            url = event["target"].buffer.find(utils.http.REGEX_URL)
            if url:
                url = re.search(utils.http.REGEX_URL, url.message).group(0)
        if not url:
            raise utils.EventError("No URL provided/found.")

        if url:
            event["stdout"].write("Shortened URL: %s" % self._shortlink(url))
        else:
            event["stderr"].write("Unable to shorten that URL.")
