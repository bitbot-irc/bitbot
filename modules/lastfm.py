#--depends-on commands
#--depends-on config
#--require-config lastfm-api-key

from datetime import datetime, timezone
from src import ModuleManager, utils

URL_SCROBBLER = "http://ws.audioscrobbler.com/2.0/"

@utils.export("set", utils.Setting("lastfm", "Set last.fm username",
    example="jesopo"))
class Module(ModuleManager.BaseModule):
    _name = "last.fm"

    @utils.hook("received.command.np", alias_of="nowplaying")
    @utils.hook("received.command.listening", alias_of="nowplaying")
    @utils.hook("received.command.nowplaying")
    def np(self, event):
        """
        :help: Get the last listened to track from a user
        :usage: [username]
        """
        user = None
        lastfm_username = None
        shown_username = None

        if event["args"]:
            arg_username = event["args_split"][0]
            if event["server"].has_user_id(arg_username):
                user = event["server"].get_user(event["args_split"][0])
            else:
                lastfm_username = shown_username = arg_username
        else:
            user = event["user"]

        if user:
            lastfm_username = user.get_setting("lastfm", user.nickname)
            shown_username = user.nickname

        page = utils.http.request(URL_SCROBBLER, get_params={
            "method": "user.getrecenttracks", "user": lastfm_username,
            "api_key": self.bot.config["lastfm-api-key"],
            "format": "json", "limit": "1"}, json=True)
        if page:
            if "recenttracks" in page.data and len(page.data["recenttracks"
                    ]["track"]):
                now_playing = page.data["recenttracks"]["track"]
                if type(now_playing) == list:
                    now_playing = now_playing[0]

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

                short_url = self.exports.get_one("search-youtube")(ytquery)
                short_url = " - " + short_url if short_url else ""

                info_page = utils.http.request(URL_SCROBBLER, get_params={
                    "method": "track.getInfo", "artist": artist,
                    "track": track_name, "autocorrect": "1",
                    "api_key": self.bot.config["lastfm-api-key"],
                    "user": lastfm_username, "format": "json"}, json=True)
                tags = []
                if "toptags" in info_page.data.get("track", []):
                    for tag in info_page.data["track"]["toptags"]["tag"]:
                        tags.append(tag["name"])
                if tags:
                    tags = " (%s)" % ", ".join(tags)
                else:
                    tags = ""

                play_count = ""
                if ("userplaycount" in info_page.data.get("track", {}) and
                        int(info_page.data["track"]["userplaycount"]) > 0):
                    play_count = int(info_page.data["track"]["userplaycount"])
                    play_count = " (%d play%s)" % (play_count,
                        "s" if play_count > 1 else "")

                track = utils.irc.bold("%s - %s" % (artist, track_name))

                event["stdout"].write("%s %s: %s%s%s%s" % (
                    shown_username, time_language, track, play_count, tags,
                    short_url))
            else:
                event["stderr"].write(
                    "The user '%s' has never scrobbled before" % (
                    shown_username))
        else:
            raise utils.EventsResultsError()
