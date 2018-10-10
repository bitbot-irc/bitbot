import re
from src import ModuleManager, utils

REGEX_URL = re.compile("https?://\S+", re.I)

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.t", alias_of="title")
    @utils.hook("received.command.title", usage="[URL]")
    def title(self, event):
        """
        :help: Get the title of a URL
        :usage: [URL]
        """
        url = None
        if len(event["args"]) > 0:
            url = event["args_split"][0]
        else:
            url = event["target"].buffer.find(REGEX_URL)
            if url:
                url = re.search(REGEX_URL, url.message).group(0)
        if not url:
            event["stderr"].write("No URL provided/found.")
            return
        soup = utils.http.get_url(url, soup=True)
        if not soup:
            event["stderr"].write("Failed to get URL.")
            return
        title = soup.title
        if title:
            title = title.text.replace("\n", " ").replace("\r", ""
                ).replace("  ", " ").strip()
            event["stdout"].write(title)
        else:
            event["stderr"].write("No title found.")
