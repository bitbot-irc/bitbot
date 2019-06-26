#--depends-on commands
#--depends-on config

import re
from src import ModuleManager, utils

URL_BITLYSHORTEN = "https://api-ssl.bitly.com/v3/shorten"

@utils.export("serverset", {"setting": "url-shortener",
    "help": "Set URL shortener service", "example": "bitly"})
@utils.export("botset", {"setting": "url-shortener",
    "help": "Set URL shortener service", "example": "bitly"})
class Module(ModuleManager.BaseModule):
    def on_load(self):
        self.exports.add("shorturl", self._shorturl)
        self.exports.add("shorturl-any", self._shorturl_any)

        self.exports.add("shorturl-s-bitly", self._bitly)

    def _get_shortener(self, name):
        return self.exports.get_one("shorturl-s-%s" % name, None)
    def _call_shortener(self, shortener_name, url):
        shortener = self._get_shortener(shortener_name)
        if shortener == None:
            return None
        short_url = shortener(url)
        if short_url == None:
            return None
        return short_url

    def _shorturl_any(self, url):
        return self._call_shortener("bitly", url) or url

    def _shorturl(self, server, url):
        shortener_name = server.get_setting("url-shortener", "bitly")
        if shortener_name == None:
            return url
        return self._call_shortener(shortener_name, url) or url

    def _bitly(self, url):
        if len(url) < 22:
            return None

        access_token = self.bot.config.get("bitly-api-key", None)
        if access_token:
            page = utils.http.request(URL_BITLYSHORTEN, get_params={
                "access_token": access_token, "longUrl": url}, json=True)

            if page and page.data["data"]:
                return page.data["data"]["url"]
        return None

    @utils.hook("received.command.shorten")
    def shorten(self, event):
        """
        :help: Shorten a given URL
        :usage: <url>
        """
        url = None
        if len(event["args"]) > 0:
            url = event["args_split"][0]
            if not re.match(utils.http.REGEX_URL, url):
                url = "http://%s" % url
        else:
            url = event["target"].buffer.find(utils.http.REGEX_URL)
            if url:
                url = re.search(utils.http.REGEX_URL, url.message).group(0)
        if not url:
            raise utils.EventError("No URL provided/found.")

        event["stdout"].write("Shortened URL: %s" % self._shorturl(
            event["server"], url))

    @utils.hook("received.command.unshorten", min_args=1)
    def unshorten(self, event):
        url = event["args_split"][0]
        if not re.match(utils.http.REGEX_URL, url):
            url = "http://%s" % url

        try:
            response = utils.http.request(url, method="HEAD",
                allow_redirects=False)
        except:
            response = None

        if response and "location" in response.headers:
            event["stdout"].write("Unshortened: %s" %
                response.headers["location"])
        else:
            event["stderr"].write("Failed to unshorten URL")
