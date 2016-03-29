import Utils

URL_SCROBBLER = "http://ws.audioscrobbler.com/2.0/"

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("boot").on("done").hook(self.boot_done)
        bot.events.on("received").on("command").on("np",
            "listening", "nowplaying").hook(self.np,
            help="Get the last listen to track from a user")

    def boot_done(self, event):
        self.bot.events.on("postboot").on("configure").on(
            "set").call(setting="lastfm",
            help="Set username on last.fm")

    def np(self, event):
        if event["args_split"]:
            username = event["args_split"][0]
        else:
            username = event["user"].get_setting("lastfm",
                event["user"].nickname)
        page = Utils.get_url(URL_SCROBBLER, get_params={
            "method": "user.getrecenttracks", "user": username,
            "api_key": self.bot.config["lastfm-api-key"],
            "format": "json", "limit": "1"}, json=True)
        if page:
            if "recenttracks" in page and len(page["recenttracks"
                    ]["track"]):
                now_playing = page["recenttracks"]["track"][0]
                track_name = now_playing["name"]
                artist = now_playing["artist"]["#text"]

                tags_page = Utils.get_url(URL_SCROBBLER, get_params={
                    "method": "track.getTags", "artist": artist,
                    "track": track_name, "autocorrect": "1",
                    "api_key": self.bot.config["lastfm-api-key"],
                    "user": username, "format": "json"}, json=True)
                tags = []
                if tags_page.get("tags", {}).get("tag"):
                    for tag in tags_page["tags"]["tag"]:
                        tags.append(tag["name"])
                if tags:
                    tags = " (%s)" % ", ".join(tags)
                else:
                    tags = ""

                event["stdout"].write("%s is now playing: %s - %s%s" % (
                    username, artist, track_name, tags))
            else:
                event["stderr"].write(
                    "The user '%s' has never scrobbled before" % (
                    username))
        else:
            event["stderr"].write("Failed to load results")
