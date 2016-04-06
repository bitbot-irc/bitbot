import json
import Utils

URL_SPOTIFY = "https://api.spotify.com/v1/search"

class Module(object):
    def __init__(self, bot):
        bot.events.on("received").on("command").on("spotify").hook(
            self.spotify, help="Search for a track on spotify",
            min_args=1)

    def spotify(self, event):
        page = Utils.get_url(URL_SPOTIFY, get_params={"type": "track",
            "limit": 1, "q": event["args"]}, json=True)
        if page:
            if len(page["tracks"]["items"]):
                item = page["tracks"]["items"][0]
                title = item["name"]
                artist_name = item["artists"][0]["name"]
                url = item["external_urls"]["spotify"]
                event["stdout"].write("%s (by %s) %s" % (title, artist_name,
                    url))
            else:
                event["stderr"].write("No results found")
        else:
            event["stderr"].write("Failed to load results")
