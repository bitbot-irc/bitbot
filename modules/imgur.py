#--depends-on commands
#--depends-on config
#--require-config imgur-api-key

import re, datetime
from src import ModuleManager, utils, EventManager

REGEX_IMAGE = re.compile("https?://(?:i\.)?imgur.com/(\w+)")
REGEX_GALLERY = re.compile("https?://imgur.com/gallery/(\w+)")

GALLERY_FORMAT = "%s%s%sA gallery with %s image%s, %s views, posted %s (%s%s)%s"
IMAGE_FORMAT = "%s%s%sA %s image, %sx%s, with %s views, posted %s%s"

URL_IMAGE = "https://api.imgur.com/3/image/%s"
URL_GALLERY = "https://api.imgur.com/3/gallery/%s"

ARROW_UP = "↑"
ARROW_DOWN = "↓"

NSFW_TEXT = "(NSFW)"


@utils.export("channelset",
              utils.BoolSetting("auto-imgur",
                                "Disable/Enable automatically getting info from Imgur URLs"))
class Module(ModuleManager.BaseModule):

    def _prefix(self, data):
        text = "%s: " % data["id"]
        if data["nsfw"]:
            text += "[NSFW] "
        if data["account_url"]:
            text += "%s " % data["account_url"]
        return text

    @utils.hook("command.regex")
    @utils.kwarg("ignore_action", False)
    @utils.kwarg("command", "imgur")
    @utils.kwarg("pattern", REGEX_IMAGE)
    def _regex_image(self, event):
        if event["target"].get_setting("auto-imgur", False):
            event["stdout"].write(self._parse_image(event["match"].group(1)))
            event.eat()

    @utils.hook("command.regex")
    @utils.kwarg("ignore_action", False)
    @utils.kwarg("command", "imgur")
    @utils.kwarg("pattern", REGEX_GALLERY)
    def _regex_gallery(self, event):
        if event["target"].get_setting("auto-imgur", False):
            event["stdout"].write(self._parse_gallery(event["match"].group(1)))
            event.eat()

    def _parse_gallery(self, hash):
        api_key = self.bot.config["imgur-api-key"]
        result = utils.http.request(URL_GALLERY % hash,
                                    headers={
                                        "Authorization": "Client-ID %s" % api_key
                                    }).json()

        if result and result["success"]:
            data = result["data"]
            text = ""

            nsfw = utils.irc.bold(NSFW_TEXT) + " " if data["nsfw"] else ""
            title = data["title"] + " " if data["title"] else ""
            views = data["views"]
            time = datetime.datetime.utcfromtimestamp(data["datetime"]). \
                strftime("%e %b, %Y at %H:%M")
            ups = utils.irc.color(str(data["ups"]) + ARROW_UP, utils.consts.GREEN)
            downs = utils.irc.color(ARROW_DOWN + str(data["downs"]), utils.consts.RED)
            images = data["images_count"]
            image_plural = "" if images == 1 else "s"

            bracket_left = "(" if title or nsfw else ""
            bracket_right = ")" if title or nsfw else ""

            return GALLERY_FORMAT % (nsfw,
                                     title,
                                     bracket_left,
                                     images,
                                     image_plural,
                                     views,
                                     time,
                                     ups,
                                     downs,
                                     bracket_right)

    def _parse_image(self, hash):
        api_key = self.bot.config["imgur-api-key"]
        result = utils.http.request(URL_IMAGE % hash,
                                    headers={
                                        "Authorization": "Client-ID %s" % api_key
                                    }).json()

        if result and result["success"]:
            data = result["data"]
            text = ""

            nsfw = utils.irc.bold(NSFW_TEXT) + " " if data["nsfw"] else ""
            title = data["title"] + " " if data["title"] else ""
            type = data["type"].split("/")[-1]
            width = data["width"]
            height = data["height"]
            views = data["views"]
            time = datetime.datetime.utcfromtimestamp(data["datetime"]).\
                strftime("%e %b, %Y at %H:%M")

            #%Y-%m-%d %H:%M:%S+00:00 (UTC)

            bracket_left = "(" if title or nsfw else ""
            bracket_right = ")" if title or nsfw else ""

        return IMAGE_FORMAT % (nsfw, title, bracket_left, type, width, height, views, time, bracket_right)

    def _image_info(self, hash):
        api_key = self.bot.config["imgur-api-key"]
        result = utils.http.request(URL_IMAGE % hash,
                                    headers={
                                        "Authorization": "Client-ID %s" % api_key
                                    }).json()

        if result and result["success"]:
            data = result["data"]
            text = self._prefix(data)

            text += "(%s %dx%d, %d views)" % (data["type"], data["width"], data["height"], data["views"])
            if data["title"]:
                text += " %s" % data["title"]
            return text
        else:
            return None

    def _gallery_info(self, hash):
        api_key = self.bot.config["imgur-api-key"]
        result = utils.http.request(URL_GALLERY % hash,
                                    headers={
                                        "Authorization": "Client-ID %s" % api_key
                                    }).json()

        if result and result["success"]:
            data = result["data"]
            text = self._prefix(data)
            text += "(%d views, %d??%d)" % (data["views"], data["ups"], data["downs"])
            if data["title"]:
                text += " %s" % data["title"]
            return text
        else:
            return None

    @utils.hook("received.command.imgur", min_args=1)
    def imgur(self, event):
        """
        :help: Get information about a given imgur image URL
        :usage: <url>
        """
        image_match = REGEX_IMAGE.match(event["args_split"][0])

        result = None
        if image_match:
            result = self._image_info(image_match.group(1))
        else:
            gallery_match = REGEX_GALLERY.match(event["args_split"][0])
            if gallery_match:
                result = self._gallery_info(gallery_match.group(1))

        if result:
            event["stdout"].write(result)
        else:
            raise utils.EventResultsError()
