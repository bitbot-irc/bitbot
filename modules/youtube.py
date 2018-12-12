#--require-config google-api-key

import re
from src import ModuleManager, utils

REGEX_YOUTUBE = re.compile(
    "https?://(?:www.)?(?:youtu.be/|youtube.com/watch\?[\S]*v=)([\w\-]{11})",
    re.I)
REGEX_ISO8601 = re.compile("PT(\d+H)?(\d+M)?(\d+S)?", re.I)

URL_YOUTUBESEARCH = "https://www.googleapis.com/youtube/v3/search"
URL_YOUTUBEVIDEO = "https://www.googleapis.com/youtube/v3/videos"

URL_YOUTUBESHORT = "https://youtu.be/%s"

ARROW_UP = "↑"
ARROW_DOWN = "↓"

@utils.export("channelset", {"setting": "auto-youtube",
    "help": "Disable/Enable automatically getting info from youtube URLs",
    "validate": utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    def get_video_page(self, video_id, part):
        return utils.http.request(URL_YOUTUBEVIDEO, get_params={"part": part,
            "id": video_id, "key": self.bot.config["google-api-key"]},
            json=True)
    def video_details(self, video_id):
        snippet = self.get_video_page(video_id, "snippet")
        if snippet.data["items"]:
            snippet = snippet.data["items"][0]["snippet"]
            statistics = self.get_video_page(video_id, "statistics").data[
                "items"][0]["statistics"]
            content = self.get_video_page(video_id, "contentDetails").data[
                "items"][0]["contentDetails"]
            video_uploader = snippet["channelTitle"]
            video_title = snippet["title"]
            video_views = statistics["viewCount"]
            video_likes = statistics.get("likeCount")
            video_dislikes = statistics.get("dislikeCount")
            video_duration = content["duration"]
            video_opinions = ""
            if video_likes and video_dislikes:
                video_opinions = " (%s%s%s%s)" % (video_likes, ARROW_UP,
                    ARROW_DOWN, video_dislikes)

            match = re.match(REGEX_ISO8601, video_duration)
            video_duration = ""
            video_duration += "%s:" % match.group(1)[:-1].zfill(2
                ) if match.group(1) else ""
            video_duration += "%s:" % match.group(2)[:-1].zfill(2
                ) if match.group(2) else "00:"
            video_duration += "%s" % match.group(3)[:-1].zfill(2
                ) if match.group(3) else "00"
            return "%s (%s) uploaded by %s, %s views%s %s" % (
                video_title, video_duration, video_uploader, "{:,}".format(
                int(video_views)), video_opinions, URL_YOUTUBESHORT % video_id)

    @utils.hook("get.searchyoutube")
    def search_video(self, event):
        search = event["query"]
        video_id = ""

        search_page = utils.http.request(URL_YOUTUBESEARCH,
            get_params={"q": search, "part": "snippet",
            "maxResults": "1", "type": "video",
            "key": self.bot.config["google-api-key"]},
             json=True)

        if search_page:
            if search_page.data["pageInfo"]["totalResults"] > 0:
                video_id = search_page.data["items"][0]["id"]["videoId"]
                return "https://youtu.be/%s" % video_id

    @utils.hook("received.command.yt", alias_of="youtube")
    @utils.hook("received.command.youtube")
    def yt(self, event):
        """
        :help: Find a video on youtube
        :usage: [query/URL]
        """
        video_id = None
        search = None
        if event["args"]:
            search = event["args"]
        else:
            last_youtube = event["target"].buffer.find(REGEX_YOUTUBE)
            if last_youtube:
                search = last_youtube.message

        url_match = re.search(REGEX_YOUTUBE, search)
        if search and url_match:
            video_id = url_match.group(1)

        if search or video_id:
            if not video_id:
                search_page = utils.http.request(URL_YOUTUBESEARCH,
                    get_params={"q": search, "part": "snippet",
                    "maxResults": "1", "type": "video",
                    "key": self.bot.config["google-api-key"]},
                    json=True)
                if search_page:
                    if search_page.data["pageInfo"]["totalResults"] > 0:
                        video_id = search_page.data["items"][0]["id"]["videoId"]
                    else:
                        event["stderr"].write("No videos found")
                else:
                    raise utils.EventsResultsError()
            if video_id:
                event["stdout"].write(self.video_details(video_id))
            else:
                event["stderr"].write("No search phrase provided")
        else:
           event["stderr"].write("No search phrase provided")

    @utils.hook("received.message.channel")
    def channel_message(self, event):
        match = re.search(REGEX_YOUTUBE, event["message"])
        if match and event["channel"].get_setting("auto-youtube", False):
            youtube_id = match.group(1)
            video_details = self.video_details(youtube_id)
            if video_details:
                self.events.on("send.stdout").call(target=event["channel"],
                    message=video_details, module_name="Youtube",
                    server=event["server"])
