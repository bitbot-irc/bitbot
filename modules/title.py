import hashlib, re
from src import EventManager, ModuleManager, utils

@utils.export("channelset", {"setting": "auto-title",
    "help": "Disable/Enable automatically getting info titles from URLs",
    "validate": utils.bool_or_none})
@utils.export("channelset", {"setting": "auto-title-first",
    "help": ("Enable/disable showing who first posted a URL that was "
        "auto-titled"),
    "validate": utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    def _url_hash(self, url):
        return "sha256:%s" % hashlib.sha256(url.lower().encode("utf8")
            ).hexdigest()

    def _get_title(self, url):
        try:
            page = utils.http.request(url, soup=True)
        except utils.http.HTTPWrongContentTypeException:
            return None
        except Exception as e:
            self.log.error("failed to get URL title", [], exc_info=True)
            return None
        if page.data.title:
            return page.data.title.text.replace("\n", " ").replace(
                "\r", "").replace("  ", " ").strip()
        else:
            return None

    @utils.hook("received.message.channel",
        priority=EventManager.PRIORITY_MONITOR)
    def channel_message(self, event):
        match = re.search(utils.http.REGEX_URL, event["message"])
        if match and event["channel"].get_setting("auto-title", False):
            url = match.group(0)
            title = self._get_title(match.group(0))

            if title:
                message = title
                if event["channel"].get_setting("auto-title-first", False):
                    setting = "url-last-%s" % self._url_hash(url)
                    first_details = event["channel"].get_setting(setting, None)

                    if first_details:
                        first_nickname, first_timestamp, _ = first_details
                        timestamp_parsed = utils.iso8601_parse(first_timestamp)
                        timestamp_human = utils.datetime_human(timestamp_parsed)
                        message = "%s (first posted by %s at %s)" % (title,
                            first_nickname, timestamp_human)
                    else:
                        event["channel"].set_setting(setting,
                            [event["user"].nickname, utils.iso8601_format_now(),
                            url])


                self.events.on("send.stdout").call(target=event["channel"],
                    message=message, module_name="Title",
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
            url = event["target"].buffer.find(utils.http.REGEX_URL)
            if url:
                url = re.search(utils.http.REGEX_URL, url.message).group(0)
        if not url:
            raise utils.EventError("No URL provided/found.")

        title = self._get_title(url)

        if title:
            event["stdout"].write(title)
        else:
            event["stderr"].write("Failed to get title")
