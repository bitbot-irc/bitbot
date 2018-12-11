import json
from src import ModuleManager, utils

URL_SPOTIFY = "https://api.spotify.com/v1/search"

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.spotify", min_args=1)
    def spotify(self, event):
        """
        :help: Search for a track on spotify
        :usage: <term>
        """
        page = utils.http.request(URL_SPOTIFY, get_params=
            {"type": "track", "limit": 1, "q": event["args"]},
            json=True)
        if page:
            if len(page.data["tracks"]["items"]):
                item = page.data["tracks"]["items"][0]
                title = item["name"]
                artist_name = item["artists"][0]["name"]
                url = item["external_urls"]["spotify"]
                event["stdout"].write("%s (by %s) %s" % (title, artist_name,
                    url))
            else:
                event["stderr"].write("No results found")
        else:
            raise utils.EventsResultsError()
