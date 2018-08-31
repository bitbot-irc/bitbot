#--require-config lastfm-api-key

import Utils

URL_SCROBBLER = "http://ws.audioscrobbler.com/2.0/"

class Module(object):
    def __init__(self, bot):
        self.bot = bot

        bot.events.on("postboot").on("configure").on(
            "set").assure_call(setting="lastfm",
            help="Set username on last.fm")

        bot.events.on("received").on("command").on("np",
            "listening", "nowplaying").hook(self.np,
            help="Get the last listened to track from a user",
            usage="[username]")

    def np(self, event):
        if event["args_split"]:
            lastfm_username = event["args_split"][0]
            shown_username = lastfm_username
        else:
            lastfm_username = event["user"].get_setting("lastfm",
                event["user"].nickname)
            shown_username = event["user"].nickname
        page = Utils.get_url(URL_SCROBBLER, get_params={
            "method": "user.getrecenttracks", "user": lastfm_username,
            "api_key": self.bot.config["lastfm-api-key"],
            "format": "json", "limit": "1"}, json=True)
        if page:
            if "recenttracks" in page and len(page["recenttracks"
                    ]["track"]):
                now_playing = page["recenttracks"]["track"][0]
                track_name = now_playing["name"]
                artist = now_playing["artist"]["#text"]

                info_page = Utils.get_url(URL_SCROBBLER, get_params={
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
                    "%s is now playing: %s - %s%s%s" % (
                    shown_username, artist, track_name, play_count, tags))
            else:
                event["stderr"].write(
                    "The user '%s' has never scrobbled before" % (
                    shown_username))
        else:
            event["stderr"].write("Failed to load results")
