#--require-config lastfm-api-key

from datetime import datetime, timezone
from src import ModuleManager, utils

URL_SCROBBLER = "http://ws.audioscrobbler.com/2.0/"

@utils.export("set", {"setting": "lastfm", "help": "Set last.fm username"})
class Module(ModuleManager.BaseModule):
    _name = "last.fm"

    @utils.hook("received.command.np|listening|nowplaying")
    def np(self, event):
        """
        :help: Get the last listened to track from a user
        :usage: [username]
        """
        if event["args_split"]:
            lastfm_username = event["args_split"][0]
            shown_username = lastfm_username
        else:
            lastfm_username = event["user"].get_setting("lastfm",
                event["user"].nickname)
            shown_username = event["user"].nickname
        page = utils.http.get_url(URL_SCROBBLER, get_params={
            "method": "user.getrecenttracks", "user": lastfm_username,
            "api_key": self.bot.config["lastfm-api-key"],
            "format": "json", "limit": "1"}, json=True)
        if page:
            if "recenttracks" in page and len(page["recenttracks"
                    ]["track"]):
                now_playing = page["recenttracks"]["track"][0]
                track_name = now_playing["name"]
                artist = now_playing["artist"]["#text"]

                if '@attr' in now_playing:
                    np = True
                else:
                    played = int(now_playing["date"]["uts"])
                    dts = int(datetime.now(tz=timezone.utc).timestamp())
                    np = bool((dts - played) < 120)

                time_language = "is listening to" if np else "last " \
                                                               + "listened to"

                ytquery = " - ".join([artist, track_name])

                short_url = self.events.on(
                    "get.searchyoutube").call_for_result(
                    query=ytquery)

                short_url = " -- " + short_url if short_url else ""

                info_page = utils.http.get_url(URL_SCROBBLER, get_params={
                    "method": "track.getInfo", "artist": artist,
                    "track": track_name, "autocorrect": "1",
                    "api_key": self.bot.config["lastfm-api-key"],
                    "user": lastfm_username, "format": "json"}, json=True)
                tags = []
                if "toptags" in info_page.get("track", []):
                    for tag in info_page["track"]["toptags"]["tag"]:
                        tags.append(tag["name"])
                if tags:
                    tags = " (%s)" % ", ".join(tags)
                else:
                    tags = ""

                play_count = ""
                if "userplaycount" in info_page.get("track", []):
                    play_count = int(info_page["track"]["userplaycount"])
                    play_count = " (%d play%s)" % (play_count,
                        "s" if play_count > 1 else "")

                event["stdout"].write(
                    "%s %s: %s - %s%s%s%s" % (
                    shown_username, time_language, artist, track_name,
                    play_count,
                    tags,
                    short_url))
            else:
                event["stderr"].write(
                    "The user '%s' has never scrobbled before" % (
                    shown_username))
        else:
            event["stderr"].write("Failed to load results")
