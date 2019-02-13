#--require-config imgur-api-key

import re
from src import ModuleManager, utils, EventManager

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
                priority=EventManager.PRIORITY_MONITOR)
    def channel_message(self, event):
        if not event["channel"].get_setting("auto-imgur", False):
            return

        match_image = re.search(REGEX_IMAGE, event["message"])
        match_gallery = re.search(REGEX_GALLERY, event["message"])
        if match_image:
            self.imgur(event, 1)
        if match_gallery:
            self.imgur(event, 1)

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
    def imgur(self, event, auto: int=0):
        """
        :help: Get information about a given imgur image URL
        :usage: <url>
        """
        msg = event["args_split"][0] if auto is 1 else event["message"]

        match = REGEX_GALLERY.match(msg)
        if match:
            event["stdout"].write(self._gallery_info(match.group(1)))
            return
        match = REGEX_IMAGE.match(msg)
        if match:
            event["stdout"].write(self._image_info(match.group(1)))
            return
