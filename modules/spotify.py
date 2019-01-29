#--require-config spotify-client-id
#--require-config spotify-client-secret

import base64, json, time
from src import ModuleManager, utils

URL_SEARCH = "https://api.spotify.com/v1/search"
URL_TOKEN = "https://accounts.spotify.com/api/token"

class Module(ModuleManager.BaseModule):
    def on_load(self):
        self._token = None
        self._token_expires = None

    def _get_token(self):
        if self._token and (self._token_expires+10) < time.time():
            return self._token
        else:
            client_id = self.bot.config["spotify-client-id"]
            client_secret = self.bot.config["spotify-client-secret"]
            bearer = "%s:%s" % (client_id, client_secret)
            bearer = base64.b64encode(bearer.encode("utf8")).decode("utf8")

            page = utils.http.request(URL_TOKEN, method="POST",
                headers={"Authorization": "Basic %s" % bearer},
                post_data={"grant_type": "client_credentials"},
                json=True)
            self._token_expire = time.time()+page.data["expires_in"]
            return page.data["access_token"]

    @utils.hook("received.command.spotify", min_args=1)
    def spotify(self, event):
        """
        :help: Search for a track on spotify
        :usage: <term>
        """
        token = self._get_token()
        page = utils.http.request(URL_SPOTIFY,
            get_params={"type": "track", "limit": 1, "q": event["args"]},
            headers={"Authorization", "Bearer %s" % token},
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
