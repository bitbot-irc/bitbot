#--require-config imgur-api-key

import re
from src import ModuleManager, utils

REGEX_IMAGE = re.compile("https?://(?:i\.)?imgur.com/(\w{7})")
URL_IMAGE = "https://api.imgur.com/3/image/%s"

class Module(ModuleManager.BaseModule):
    def _image_info(self, hash):
        api_key = self.bot.config["imgur-api-key"]
        result = utils.http.get_url(URL_IMAGE % hash,
            headers={"Authorization", "Client-ID %s" % api_key},
            json=True)

        if result and result["success"]:
            data = result["data"]
            text = "%s: " % data["id"]
            if data["nsfw"]:
                text += "[NSFW] "

            text += "(%s %dx%d, %d views) " % (data["type"], data["width"],
                data["height"], data["views"])
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
        match = REGEX_IMAGE.match(event["args_split"][0])
        if match:
            event["stdout"].write(self._image_info(match.group(1)))
