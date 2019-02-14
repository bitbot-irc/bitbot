#--require-config imgur-api-key

import re, json
from src import ModuleManager, utils, EventManager, Logging
from datetime import datetime

REGEX_IMAGE = re.compile("https?://(?:i\.)?imgur.com/(\w+)")
REGEX_GALLERY = re.compile("https?://imgur.com/gallery/(\w+)")

URL_IMAGE = "https://api.imgur.com/3/image/%s"
URL_GALLERY = "https://api.imgur.com/3/gallery/%s"

@utils.export("channelset", {"setting": "auto-imgur",
    "help": "Disable/Enable automatically getting info from Imgur URLs",
    "validate": utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    def _prefix(self, data):
        text = "%s: " % data["id"]
        if data["nsfw"]:
            text += "[NSFW] "
        if data["account_url"]:
            text += "%s " % data["account_url"]
        return text

    @utils.hook("received.message.channel",
                priority=EventManager.PRIORITY_LOW)
    def channel_message(self, event):
        if not event["channel"].get_setting("auto-imgur", False):
            return

        self._imgur(event)

    def _imgur(self, event):
        msg = event["message"]
        reply = ""
        match_gallery = REGEX_GALLERY.match(msg)
        match_image = REGEX_IMAGE.match(msg)

        if match_gallery:
            reply = self._parse_gallery(match_gallery.group(1))

        if match_image and not reply:
            reply = self._parse_image(match_image.group(1))

        if not reply:
            return

        event.eat()

        self.events.on("send.stdout").call(target=event[
            "channel"], module_name="Imgur", server=event["server"],
                                           message=reply)
        return

    def _parse_gallery(self, hash):
        api_key = self.bot.config["imgur-api-key"]
        result = utils.http.request(URL_GALLERY % hash,
            headers={"Authorization": "Client-ID %s" % api_key},
            json=True)

        if result and result.data["success"]:
            data = result.data["data"]
            text = ""

            nsfw = utils.irc.bold("[NSFW] ") if data["nsfw"] else ""
            title = utils.irc.bold(data["title"]) + " " if data["title"] else ""
            views = data["views"]
            time = datetime.utcfromtimestamp(data["datetime"]). \
                strftime("%e %b, %Y at %H:%M")
            ups = utils.irc.color(str(data["ups"]) + "▲", utils.consts.GREEN)
            downs = utils.irc.color("▼" + str(data["downs"]), utils.consts.RED)
            images = data["images_count"]
            image_plural = "" if images is 1 else "s"

            bracket_left = "(" if title or nsfw else ""
            bracket_right = ")" if title or nsfw else ""

            return "%s%s%sA gallery with %s image%s, %s views, posted %s (%s%s)%s" % \
               (nsfw, title, bracket_left, images, image_plural, views,
                time, ups, downs,
                bracket_right)


    def _parse_image(self, hash):
        api_key = self.bot.config["imgur-api-key"]
        result = utils.http.request(URL_IMAGE % hash,
            headers={"Authorization": "Client-ID %s" % api_key},
            json=True)

        if result and result.data["success"]:
           # Logging.Log.debug("%s", result.data["data"])

            data = result.data["data"]
            text = ""

            nsfw = utils.irc.bold("[NSFW] ") if data["nsfw"] else ""
            title = utils.irc.bold(data["title"]) + " " if data["title"] else ""
            type = data["type"].split("/")[-1]
            width = data["width"]
            height = data["height"]
            views = data["views"]
            time = datetime.utcfromtimestamp(data["datetime"]).\
                strftime("%e %b, %Y at %H:%M")

           #%Y-%m-%d %H:%M:%S+00:00 (UTC)

            bracket_left = "(" if title or nsfw else ""
            bracket_right = ")" if title or nsfw else ""

        return "%s%s%sA %s image, %sx%s, with %s views, posted %s%s" % \
               (nsfw, title, bracket_left, type, width, height, views, time,
                bracket_right)



    def _image_info(self, hash):
        api_key = self.bot.config["imgur-api-key"]
        result = utils.http.request(URL_IMAGE % hash,
            headers={"Authorization": "Client-ID %s" % api_key},
            json=True)

        if result and result.data["success"]:
            data = result.data["data"]
            text = self._prefix(data)

            text += "(%s %dx%d, %d views)" % (data["type"], data["width"],
                data["height"], data["views"])
            if data["title"]:
                text += " %s" % data["title"]
            return text
        else:
            raise utils.EventsResultsError()

    def _gallery_info(self, hash):
        api_key = self.bot.config["imgur-api-key"]
        result = utils.http.request(URL_GALLERY % hash,
            headers={"Authorization": "Client-ID %s" % api_key},
            json=True)

        if result and result.data["success"]:
            data = result.data["data"]
            text = self._prefix(data)
            text += "(%d views, %d▲▼%d)" % (data["views"],
                data["ups"], data["downs"])
            if data["title"]:
                text += " %s" % data["title"]
            return text
        else:
            raise utils.EventsResultsError()

    @utils.hook("received.command.imgur", min_args=1)
    def imgur(self, event):
        """
        :help: Get information about a given imgur image URL
        :usage: <url>
        """
        msg = event["args_split"][0]

        match = REGEX_GALLERY.match(msg)
        if match:
            event["stdout"].write(self._gallery_info(match.group(1)))
            return

        match = REGEX_IMAGE.match(event["args_split"][0])
        if match:
            event["stdout"].write(self._image_info(match.group(1)))
            return
