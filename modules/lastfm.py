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
            if ("recenttracks" in page.data and
                    len(page.data["recenttracks"]["track"])):
                now_playing = page.data["recenttracks"]["track"]
                if type(now_playing) == list:
                    now_playing = now_playing[0]

                track_name = now_playing["name"]
                artist = now_playing["artist"]["#text"]

                if '@attr' in now_playing:
                    np = True
                else:
                    played = int(now_playing["date"]["uts"])
                    dt = utils.datetime.datetime_utcnow()
                    np = bool((dt.timestamp()-played) < 120)

                time_language = "is listening to" if np else "last listened to"

                yt_url = self.exports.get_one("search-youtube")(
                    "%s - %s" % (artist, track_name))
                yt_url_str = ""
                if yt_url:
                    yt_url_str = " - %s" % yt_url

                info_page = utils.http.request(URL_SCROBBLER, get_params={
                    "method": "track.getInfo", "artist": artist,
                    "track": track_name, "autocorrect": "1",
                    "api_key": self.bot.config["lastfm-api-key"],
                    "user": lastfm_username, "format": "json"}, json=True)

                track = info_page.data.get("track", {})

                tags_str = ""
                if "toptags" in track:
                    tags = [t["name"] for t in track["toptags"]["tag"]]
                    tags_str = " [%s]" % ", ".join(tags)

                play_count_str = ""
                if "userplaycount" in track:
                    play_count = int(track["userplaycount"])
                    if play_count > 0:
                        play_count_str = " (%d play%s)" % (play_count,
                            "" if play_count == 1 else "s")

                track_name = utils.irc.bold("%s - %s" % (artist, track_name))

                event["stdout"].write("%s %s: %s%s%s%s" % (
                    shown_username, time_language, track_name, play_count_str,
                    tags_str, yt_url_str))
            else:
                event["stderr"].write(
                    "The user '%s' has never scrobbled before" % (
                    shown_username))
        else:
            raise utils.EventResultsError()
