#--depends-on commands
#--depends-on config
#--require-config google-api-key

import datetime, re, urllib.parse
from src import EventManager, ModuleManager, utils

REGEX_YOUTUBE = re.compile("https?://(?:www\.|m\.|music\.)?(?:youtu.be/|youtube.com/)\\S+", re.I)

URL_YOUTUBESEARCH = "https://www.googleapis.com/youtube/v3/search"
URL_YOUTUBEVIDEO = "https://www.googleapis.com/youtube/v3/videos"
URL_YOUTUBEPLAYLIST = "https://www.googleapis.com/youtube/v3/playlists"

URL_YOUTUBESHORT = "https://youtu.be/%s"
URL_VIDEO = "https://www.youtube.com/watch?v=%s"
URL_PLAYLIST = "https://www.youtube.com/playlist?list=%s"

ARROW_UP = "↑"
ARROW_DOWN = "↓"

@utils.export("channelset", utils.BoolSetting("auto-youtube",
    "Disable/Enable automatically getting info from youtube URLs"))
@utils.export("channelset", utils.BoolSetting("youtube-safesearch",
    "Turn safe search off/on"))
class Module(ModuleManager.BaseModule):
    def get_video_page(self, video_id):
        self.log.debug("youtube API request: "
            "videos.list [contentDetails,snippet,statistics]")
        return utils.http.request(URL_YOUTUBEVIDEO, get_params={
            "part": "contentDetails,snippet,statistics",
            "id": video_id, "key": self.bot.config["google-api-key"]}).json()

    def _number(self, n):
        if n:
            return "{:,}".format(int(n))

    def video_details(self, video_id):
        page = self.get_video_page(video_id)
        try:
            if page["items"]:
                item = page["items"][0]
                snippet = item["snippet"]
                statistics = item["statistics"]
                content = item["contentDetails"]

                video_uploaded_at = utils.datetime.parse.iso8601(
                    snippet["publishedAt"])
                video_uploaded_at = utils.datetime.format.date_human(
                    video_uploaded_at)

                video_uploader = snippet["channelTitle"]
                video_title = utils.irc.bold(snippet["title"])

                video_views = self._number(statistics.get("viewCount"))
                video_likes = self._number(statistics.get("likeCount"))
                video_dislikes = self._number(statistics.get("dislikeCount"))

                video_opinions = ""
                if video_likes and video_dislikes:
                    likes = utils.irc.color("%s%s" % (video_likes, ARROW_UP),
                        utils.consts.GREEN)
                    dislikes = utils.irc.color("%s%s" %
                        (ARROW_DOWN, video_dislikes), utils.consts.RED)
                    video_opinions = " (%s%s)" % (likes, dislikes)

                video_views_str = ""
                if video_views:
                    video_views_str = ", %s views" % video_views

                td = utils.datetime.parse.iso8601_duration(content["duration"])
                video_duration = utils.datetime.format.to_pretty_time(
                    td.total_seconds())

                url = URL_YOUTUBESHORT % video_id

                return "%s (%s) uploaded by %s on %s%s%s" % (
                    video_title, video_duration, video_uploader, video_uploaded_at,
                    video_views_str, video_opinions), url
            return None
        except KeyError:
            return None

    def get_playlist_page(self, playlist_id):
        self.log.debug("youtube API request: "
            "playlists.list [contentDetails,snippet]")

        return utils.http.request(URL_YOUTUBEPLAYLIST, get_params={
            "part": "contentDetails,snippet", "id": playlist_id,
            "key": self.bot.config["google-api-key"]}).json()
    def playlist_details(self, playlist_id):
        page = self.get_playlist_page(playlist_id)
        try:
            if page["items"]:
                item = page["items"][0]
                snippet = item["snippet"]
                content = item["contentDetails"]

                count = content["itemCount"]

                return "%s - %s (%s %s)" % (snippet["channelTitle"],
                    snippet["title"], count, "video" if count == 1 else "videos"
                    ), URL_PLAYLIST % playlist_id
        except KeyError:
            return None

    def _from_url(self, url):
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)

        if parsed.hostname == "youtu.be" and parsed.path:
            return self.video_details(parsed.path[1:])
        elif parsed.path == "/watch" and "v" in query:
            return self.video_details(query["v"][0])
        elif parsed.path.startswith("/shorts/"):
            return self.video_details(parsed.path.split("/shorts/", 1)[1])
        elif parsed.path.startswith("/embed/"):
            return self.video_details(parsed.path.split("/embed/", 1)[1])
        elif parsed.path == "/playlist" and "list" in query:
            return self.playlist_details(query["list"][0])

    @utils.export("search-youtube")
    def _search_youtube(self, query):
        video_id = ""

        self.log.debug("youtube API request: search.list (A) [snippet]")

        search_page = utils.http.request(URL_YOUTUBESEARCH,
            get_params={"q": query, "part": "snippet",
            "maxResults": "1", "type": "video",
            "key": self.bot.config["google-api-key"]}).json()

        if search_page:
            if search_page["pageInfo"]["totalResults"] > 0:
                video_id = search_page["items"][0]["id"]["videoId"]
                return "https://youtu.be/%s" % video_id

    @utils.hook("received.command.yt", alias_of="youtube")
    @utils.hook("received.command.youtube")
    def yt(self, event):
        """
        :help: Find a video on youtube
        :usage: [query/URL]
        """
        url = None
        search = None
        if event["args"]:
            search = event["args"]
            url_match = re.match(REGEX_YOUTUBE, event["args"])
            if url_match:
                url = event["args"]
            else:
                search = event["args"]
        else:
            url = event["target"].buffer.find(REGEX_YOUTUBE)
            url = utils.http.url_sanitise(url.match) if url else None

        from_url = not url == None


        try:
            if not url:
                safe_setting = event["target"].get_setting("youtube-safesearch", True)
                safe = "moderate" if safe_setting else "none"

                self.log.debug("youtube API request: search.list (B) [snippet]")

                search_page = utils.http.request(URL_YOUTUBESEARCH,
                    get_params={"q": search, "part": "snippet", "maxResults": "1",
                    "type": "video", "key": self.bot.config["google-api-key"],
                    "safeSearch": safe}).json()
                if search_page:
                    if search_page["pageInfo"]["totalResults"] > 0:
                        url = URL_VIDEO % search_page["items"][0]["id"]["videoId"]
                    else:
                        raise utils.EventError("No videos found")
                else:
                    raise utils.EventResultsError()
        except KeyError:
            raise utils.EventError("API error")

        if url:
            out = self._from_url(url)
            if not out == None:
                out, short_url = out
                if not from_url:
                    out = "%s %s" % (out, short_url)
                event["stdout"].write(out)
            else:
                raise utils.EventResultsError()
        else:
            event["stderr"].write("No search phrase provided")

    @utils.hook("command.regex")
    @utils.kwarg("ignore_action", False)
    @utils.kwarg("command", "youtube")
    @utils.kwarg("pattern", REGEX_YOUTUBE)
    def channel_message(self, event):
        if event["target"].get_setting("auto-youtube", False):
            url = utils.http.url_sanitise(event["match"].group(0))
            out = self._from_url(url)
            if not out == None:
                out, short_url = out
                event.eat()
                event["stdout"].write(out)
