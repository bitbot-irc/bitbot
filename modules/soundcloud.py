#--require-config soundcloud-api-key

import json, re, time
from src import ModuleManager, Utils

URL_SOUNDCLOUD_TRACK = "http://api.soundcloud.com/tracks"
URL_SOUNDCLOUD_RESOLVE = "http://api.soundcloud.com/resolve"
REGEX_SOUNDCLOUD = "https?://soundcloud.com/([^/]+)/([^/]+)"

class Module(ModuleManager.BaseModule):
    _name = "SoundCloud"

    @Utils.hook("received.command.soundcloud|sc")
    def soundcloud(self, event):
        """
        :help: Search SoundCloud
        :usage: <term>
        """
        query = None
        url = None

        if event["args"]:
            match = re.search(REGEX_SOUNDCLOUD, event["args"])
            if match:
                url = match.string
            else:
                query = event["args"]
        else:
            last_soundcloud = event["target"].buffer.find(REGEX_SOUNDCLOUD)
            if last_soundcloud:
                url = re.match(REGEX_SOUNDCLOUD,
                    last_soundcloud.message).string

        if not query and not url:
            event["stderr"].write("no search phrase provided")
            return
        has_query = not query == None
        get_params = {"limit": 1,
            "client_id": self.bot.config["soundcloud-api-key"]}

        if query:
            get_params["q"] = query
        else:
            get_params["url"] = url

        page = Utils.get_url(
            URL_SOUNDCLOUD_TRACK if has_query else URL_SOUNDCLOUD_RESOLVE,
            get_params=get_params, json=True)

        if page:
            page = page[0] if has_query else page
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
            event["stderr"].write("Failed to load results")
