#--require-config soundcloud-api-key

import json, time
import Utils

URL_SOUNDCLOUD = "http://api.soundcloud.com/tracks"

class Module(object):
    _name = "SoundCloud"
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("command").on("soundcloud", "sc"
            ).hook(self.soundcloud, min_args=1, help="Search SoundCloud")

    def soundcloud(self, event):
        page = Utils.get_url(URL_SOUNDCLOUD, get_params={
            "client_id": self.bot.config["soundcloud-api-key"],
            "limit": 1, "q": event["args"]}, json=True)
        if page:
            if page:
                page = page[0]
                title = page["title"]
                user = page["user"]["username"]
                duration = time.strftime("%H:%M:%S", time.gmtime(page[
                    "duration"]/1000))
                if duration.startswith("00:"):
                    duration = duration[3:]
                link = page["permalink_url"]
                event["stdout"].write("%s [%s] (posted by %s) %s" % (title,
                    duration, user, link))
            else:
                event["stderr"].write("No results found")
        else:
            event["stderr"].write("Failed to load results")
