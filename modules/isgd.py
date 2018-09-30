import re
from src import ModuleManager, Utils

ISGD_API_URL = "https://is.gd/create.php"
REGEX_URL = re.compile("https?://", re.I)

class Module(ModuleManager.BaseModule):
    @Utils.hook("get.shortlink")
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

    @Utils.hook("received.command.shorten", min_args=1)
    def shorten(self, event):
        """
        :help: Shorten a given URL using the is.gd service
        :usage: <url>
        """
        link = self.events.on("get.shortlink").call_for_result(
            url=event["args"])
        if link:
            event["stdout"].write("Shortened URL: %s" % link)
        else:
            event["stderr"].write("Unable to shorten that URL.")
