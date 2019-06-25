#--depends-on commands
#--require-config bitly-api-key

import re
from src import ModuleManager, utils

URL_BITLYSHORTEN = "https://api-ssl.bitly.com/v3/shorten"

class Module(ModuleManager.BaseModule):
    def on_load(self):
        self.exports.add("shorturl-s-bitly", self._shorturl)
    def _shorturl(self, url):
        if len(url) < 22:
            return None

        page = utils.http.request(URL_BITLYSHORTEN, get_params={
            "access_token": self.bot.config["bitly-api-key"],
            "longUrl": url}, json=True)

        if page and page.data["data"]:
            return page.data["data"]["url"]
        return None
