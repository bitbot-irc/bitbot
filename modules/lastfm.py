#--depends-on commands
#--depends-on config
#--require-config lastfm-api-key

from datetime import datetime, timezone
from src import ModuleManager, utils

URL_SCROBBLER = "http://ws.audioscrobbler.com/2.0/"

SETTING_YT = utils.BoolSetting("lastfm-youtube",
    "Whether or not to search last.fm now-playing results on youtube")

@utils.export("set", utils.Setting("lastfm", "Set last.fm username",
    example="jesopo"))
@utils.export("botset", SETTING_YT)
@utils.export("serverset", SETTING_YT)
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
            "format": "json", "limit": "1"}).json()
        if page:
            if "recenttracks" in page and len(page["recenttracks"]["track"]):
                now_playing = page["recenttracks"]["track"]
                if type(now_playing) == list:
                    now_playing = now_playing[0]

                track_name = now_playing["name"]
                artist = now_playing["artist"]["#text"]

                if '@attr' in now_playing:
                    np = True
                else:
                    played = int(now_playing["date"]["uts"])
                    dt = utils.datetime.utcnow()
                    np = bool((dt.timestamp()-played) < 120)

                time_language = "is listening to" if np else "last listened to"

                yt_url_str = ""
                if event["server"].get_setting("lastfm-youtube",
                        self.bot.get_setting("lastfm-youtube", False)):
                    yt_url = self.exports.get("search-youtube")(
                        "%s - %s" % (artist, track_name))
                    if yt_url:
                        yt_url_str = " - %s" % yt_url

                info_page = utils.http.request(URL_SCROBBLER, get_params={
                    "method": "track.getInfo", "artist": artist,
                    "track": track_name, "autocorrect": "1",
                    "api_key": self.bot.config["lastfm-api-key"],
                    "user": lastfm_username, "format": "json"}).json()

                track = info_page.get("track", {})

                tags_str = ""
                if "toptags" in track and track["toptags"]["tag"]:
                    tags_list = track["toptags"]["tag"]
                    if not type(tags_list) == list:
                        tags_list = [tags_list]
                    tags = [t["name"] for t in tags_list]
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
