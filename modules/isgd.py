import re
from src import ModuleManager, utils

ISGD_API_URL = "https://is.gd/create.php"
REGEX_URL = re.compile("https?://", re.I)

class Module(ModuleManager.BaseModule):
    def on_load(self):
        self.exports.add("shortlink", self._shortlink)

    def _shortlink(self, url):
        if not re.match(REGEX_URL, url):
            url = "http://%s" % url

        page = utils.http.request(ISGD_API_URL, get_params=
            {"format": "json", "url": url}, json=True)

        if page and page.data["shorturl"]:
            return page.data["shorturl"]

    @utils.hook("received.command.shorten", min_args=1)
    def shorten(self, event):
        """
        :help: Shorten a given URL using the is.gd service
        :usage: <url>
        """
        link = self._shortlink(event["args"])
        if link:
            event["stdout"].write("Shortened URL: %s" % link)
        else:
            event["stderr"].write("Unable to shorten that URL.")
