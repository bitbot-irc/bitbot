#--require-config imgur-api-key

import re
from src import ModuleManager, utils

REGEX_IMAGE = re.compile("https?://(?:i\.)?imgur.com/(\w+)")
REGEX_GALLERY = re.compile("https?://imgur.com/gallery/(\w+)")

URL_IMAGE = "https://api.imgur.com/3/image/%s"
URL_GALLERY = "https://api.imgur.com/3/gallery/%s"

class Module(ModuleManager.BaseModule):
    def _prefix(self, data):
        text = "%s: " % data["id"]
        if data["nsfw"]:
            text += "[NSFW] "
        if data["account_url"]:
            text += "%s " % data["account_url"]
        return text

    def _image_info(self, hash):
        api_key = self.bot.config["imgur-api-key"]
        result = utils.http.get_url(URL_IMAGE % hash,
            headers={"Authorization": "Client-ID %s" % api_key},
            json=True)

        if result and result["success"]:
            data = result["data"]
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
        result = utils.http.get_url(URL_GALLERY % hash,
            headers={"Authorization": "Client-ID %s" % api_key},
            json=True)

        if result and result["success"]:
            data = result["data"]
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
        match = REGEX_GALLERY.match(event["args_split"][0])
        if match:
            event["stdout"].write(self._gallery_info(match.group(1)))
            return
        match = REGEX_IMAGE.match(event["args_split"][0])
        if match:
            event["stdout"].write(self._image_info(match.group(1)))
            return
