#--depends-on commands
#--depends-on config
#--depends-on shorturl

import hashlib, re, urllib.parse
from src import EventManager, ModuleManager, utils

@utils.export("channelset", utils.BoolSetting("auto-title",
    "Disable/Enable automatically getting info titles from URLs"))
@utils.export("channelset", utils.BoolSetting("title-shorten",
    "Enable/disable shortening URLs when getting their title"))
@utils.export("channelset", utils.BoolSetting("auto-title-first",
    "Enable/disable showing who first posted a URL that was auto-titled"))
class Module(ModuleManager.BaseModule):
    def _url_hash(self, url):
        return "sha256:%s" % hashlib.sha256(url.lower().encode("utf8")
            ).hexdigest()

    def _get_title(self, server, channel, url):
        if not urllib.parse.urlparse(url).scheme:
            url = "http://%s" % url

        hostname = urllib.parse.urlparse(url).hostname
        if utils.http.is_localhost(hostname):
            self.log.warn("tried to get title of localhost: %s", [url])
            return None

        try:
            page = self.bot.http_client().request(url, parse=True)
        except utils.http.HTTPWrongContentTypeException:
            return None
        except Exception as e:
            self.log.error("failed to get URL title: %s", [url], exc_info=True)
            return None
        if page.data.title:
            title = page.data.title.text.replace("\n", " ").replace(
                "\r", "").replace("  ", " ").strip()

            if channel.get_setting("title-shorten", False):
                short_url = self.exports.get_one("shorturl")(server, url,
                    context=channel)
                return "%s - %s" % (title, short_url)
            return title
        else:
            return None

    @utils.hook("command.regex")
    @utils.kwarg("ignore_action", False)
    @utils.kwarg("priority", EventManager.PRIORITY_MONITOR)
    @utils.kwarg("command", "title")
    @utils.kwarg("pattern", utils.http.REGEX_URL)
    def channel_message(self, event):
        if event["target"].get_setting("auto-title", False):
            event.eat()
            url = utils.http.url_sanitise(event["match"].group(0))
            title = self._get_title(event["server"], event["target"], url)

            if title:
                message = title
                if event["target"].get_setting("auto-title-first", False):
                    setting = "url-last-%s" % self._url_hash(url)
                    first_details = event["target"].get_setting(setting, None)

                    if first_details:
                        first_nickname, first_timestamp, _ = first_details
                        timestamp_parsed = utils.iso8601_parse(first_timestamp)
                        timestamp_human = utils.datetime_human(timestamp_parsed)
                        message = "%s (first posted by %s at %s)" % (title,
                            first_nickname, timestamp_human)
                    else:
                        event["target"].set_setting(setting,
                            [event["user"].nickname, utils.iso8601_format_now(),
                            url])
                event["stdout"].write(message)

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
            match = event["target"].buffer.find(utils.http.REGEX_URL)
            if match:
                url = match.match
        if not url:
            raise utils.EventError("No URL provided/found.")

        title = self._get_title(event["server"], event["target"], url)

        if title:
            event["stdout"].write(title)
        else:
            event["stderr"].write("Failed to get title")
