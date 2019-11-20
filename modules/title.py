#--depends-on commands
#--depends-on config
#--depends-on shorturl

import hashlib, re, urllib.parse
from src import EventManager, ModuleManager, utils

RE_WORDSPLIT = re.compile("[\s/]")

@utils.export("channelset", utils.BoolSetting("auto-title",
    "Disable/Enable automatically getting info titles from URLs"))
@utils.export("channelset", utils.BoolSetting("title-shorten",
    "Enable/disable shortening URLs when getting their title"))
@utils.export("channelset", utils.BoolSetting("auto-title-first",
    "Enable/disable showing who first posted a URL that was auto-titled"))
@utils.export("channelset", utils.BoolSetting("auto-title-difference",
    "Enable/disable checking if a <title> is different enough from the URL"
    " before showing it"))
class Module(ModuleManager.BaseModule):
    def _url_hash(self, url):
        return "sha256:%s" % hashlib.sha256(url.lower().encode("utf8")
            ).hexdigest()

    def _different(self, url, title):
        url = url.lower()
        title_words = []
        for title_word in RE_WORDSPLIT.split(title):
            if len(title_word) > 1 or title_word.isalpha():
                title_word = title_word.lower()
                title_words.append(title_word.strip("'\"<>()"))

        present = 0
        for title_word in title_words:
            if title_word in url:
                present += 1

        similarity = present/len(title_words)
        # if at least 80% of words are in the URL, too similar
        if similarity >= 0.8:
            return False
        return True

    def _get_title(self, server, channel, url):
        if not urllib.parse.urlparse(url).scheme:
            url = "http://%s" % url

        hostname = urllib.parse.urlparse(url).hostname
        if not utils.http.host_permitted(hostname):
            self.log.warn("Attempted to get forbidden host: %s", [url])
            return -1, None

        try:
            page = utils.http.request(url, parse=True)
        except utils.http.HTTPWrongContentTypeException:
            return -1, None
        except Exception as e:
            self.log.error("failed to get URL title for %s: %s", [url, str(e)])
            return -1, None

        if page.data.title:
            title = utils.parse.line_normalise(page.data.title.text)
            if not title:
                return -3, None

            if channel:
                if (channel.get_setting("auto-title-difference", True) and
                        not self._different(url, title)):
                    return -2, title

                if channel.get_setting("title-shorten", False):
                    short_url = self.exports.get_one("shorturl")(server, url,
                        context=channel)
                    return page.code, "%s - %s" % (title, short_url)
            return page.code, title
        else:
            return -1, None

    @utils.hook("command.regex")
    @utils.kwarg("ignore_action", False)
    @utils.kwarg("priority", EventManager.PRIORITY_MONITOR)
    @utils.kwarg("command", "title")
    @utils.kwarg("pattern", utils.http.REGEX_URL)
    def channel_message(self, event):
        if event["target"].get_setting("auto-title", False):
            event.eat()
            url = utils.http.url_sanitise(event["match"].group(0))
            code, title = self._get_title(event["server"], event["target"], url)

            if code == 200 and title:
                message = title
                if event["target"].get_setting("auto-title-first", False):
                    setting = "url-last-%s" % self._url_hash(url)
                    first_details = event["target"].get_setting(setting, None)

                    if first_details:
                        first_nickname, first_timestamp, _ = first_details
                        timestamp_parsed = utils.datetime.iso8601_parse(
                            first_timestamp)
                        timestamp_human = utils.datetime.datetime_human(
                            timestamp_parsed)

                        message = "%s (first posted by %s at %s)" % (title,
                            first_nickname, timestamp_human)
                    else:
                        event["target"].set_setting(setting,
                            [event["user"].nickname,
                            utils.datetime.iso8601_format_now(), url])
                event["stdout"].write(message)
            if code == -2:
                self.log.debug("Not showing title for %s, too similar", [url])

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

        channel = None
        if event["is_channel"]:
            channel = event["target"]
        code, title = self._get_title(event["server"], channel, url)

        if title:
            event["stdout"].write(title)
        else:
            event["stderr"].write("Failed to get title")

    @utils.hook("received.command.notitle")
    @utils.kwarg("expect_output", False)
    def notitle(self, event):
        pass
