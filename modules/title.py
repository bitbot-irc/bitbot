import re
from src import ModuleManager, utils

REGEX_URL = re.compile("https?://\S+", re.I)

@utils.export("channelset", {"setting": "auto-title",
    "help": "Disable/Enable automatically getting info titles from URLs",
    "validate": utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    def _get_title(self, url):
        try:
            page = utils.http.request(url, soup=True)
        except Exception as e:
            self.log.error("failed to get URL title", exc_info=True)
            return None
        if page.data.title:
            return page.data.title.text.replace("\n", " ").replace(
                "\r", "").replace("  ", " ").strip()
        else:
            return None

    @utils.hook("received.message.channel",
        priority=EventManager.PRIORITY_MONITOR)
    def channel_message(self, event):
        match = re.search(REGEX_URL, event["message"])
        if match and event["channel"].get_setting("auto-title", False):
            title = self._get_title(match.group(0))
            if title:
                self.events.on("send.stdout").call(target=event["channel"],
                    message=title, module_name="Title",
                    server=event["server"])

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
            raise utils.EventError("No URL provided/found.")

        title = self._get_title(url)

        if title:
            title = title.text.replace("\n", " ").replace("\r", ""
                ).replace("  ", " ").strip()
            event["stdout"].write(title)
        else:
            event["stderr"].write("Failed to get title")
