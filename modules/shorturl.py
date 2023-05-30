#--depends-on commands
#--depends-on config

import re
from src import ModuleManager, utils

URL_BITLYSHORTEN = "https://api-ssl.bitly.com/v4/shorten"

class Module(ModuleManager.BaseModule):
    def on_load(self):
        setting = utils.OptionsSetting([], "url-shortener",
            "Set URL shortener service",
            options_factory=self._shorturl_options_factory)
        self.exports.add("channelset", setting)
        self.exports.add("serverset", setting)
        self.exports.add("botset", setting)

    def _shorturl_options_factory(self):
        shorteners = set(self.exports.find("shorturl-s-"))
        shorteners.update(self.exports.find("shorturl-x-"))
        return sorted(s.split("-", 2)[-1] for s in shorteners)

    def _get_shortener(self, name):
        extended = self.exports.get("shorturl-x-%s" % name, None)
        if not extended == None:
            return True, extended
        return False, self.exports.get("shorturl-s-%s" % name, None)
    def _call_shortener(self, server, context, shortener_name, url):
        extended, shortener = self._get_shortener(shortener_name)
        if shortener == None:
            return None

        if extended:
            short_url = shortener(server, context, url)
        else:
            short_url = shortener(url)

        if short_url == None:
            return None
        return short_url

    @utils.export("shorturl-any")
    def _shorturl_any(self, url):
        return self._call_shortener(None, None, "bitly", url) or url

    @utils.export("shorturl")
    def _shorturl(self, server, url, context=None):
        shortener_name = None
        if context:
            shortener_name = context.get_setting("url-shortener",
                server.get_setting("url-shortener",
                self.bot.get_setting("url-shortener", "bitly")))
        else:
            shortener_name = server.get_setting("url-shortener",
                self.bot.get_setting("url-shortener", "bitly"))

        if shortener_name == None:
            return url
        return self._call_shortener(
            server, context, shortener_name, url) or url

    @utils.export("shorturl-s-bitly")
    def _bitly(self, url):
        if len(url) < 22:
            return None

        access_token = self.bot.config.get("bitly-api-key", None)
        if access_token:
            resp = utils.http.request(
                URL_BITLYSHORTEN,
                method="POST",
                post_data={"long_url": url},
                json_body=True,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if resp.code == 200:
                return resp.json()["link"]
        return None

    def _find_url(self, target, args):
        url = None
        if args:
            url = args[0]
            if not re.match(utils.http.REGEX_URL, url):
                url = "http://%s" % url
        else:
            url = target.buffer.find(utils.http.REGEX_URL)
            if url:
                url = utils.http.url_sanitise(url.match)
        if not url:
            raise utils.EventError("No URL provided/found.")
        return url

    @utils.hook("received.command.shorten")
    def shorten(self, event):
        """
        :help: Shorten a given URL
        :usage: <url>
        """
        url = self._find_url(event["target"], event["args_split"])

        event["stdout"].write("Shortened URL: %s" % self._shorturl(
            event["server"], url, context=event["target"]))

    @utils.hook("received.command.unshorten")
    def unshorten(self, event):
        url = self._find_url(event["target"], event["args_split"])

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