import re
import Utils

REGEX_URL = re.compile("https?://\S+", re.I)

class Module(object):
    def __init__(self, bot, events):
        events.on("received").on("command").on("title", "t").hook(
            self.title, help="Get the title of the provided or most "
            "recent URL.", usage="[URL]")

    def title(self, event):
        url = None
        if len(event["args"]) > 0:
            url = event["args_split"][0]
        else:
            url = event["buffer"].find(REGEX_URL)
            if url:
                url = re.search(REGEX_URL, url.message).group(0)
        if not url:
            event["stderr"].write("No URL provided/found.")
            return
        soup = Utils.get_url(url, soup=True)
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
