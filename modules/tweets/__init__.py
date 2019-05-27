#--require-config twitter-api-key
#--require-config twitter-api-secret
#--require-config twitter-access-token
#--require-config twitter-access-secret

import re
from src import ModuleManager, utils
from . import format
import tweepy

_bot = None
_events = None
_exports = None

REGEX_TWITTERURL = re.compile(
    "https?://(?:www\.)?twitter.com/[^/]+/status/(\d+)", re.I)

def _get_follows():
    return _bot.database.channel_settings.find_by_setting("twitter-follow")

class BitBotStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        data = json.loads(status)
        username = data["user"]["screen_name"].lower()

        follows = []
        for server_id, channel_name, value in _get_follows():
            if value.lower() == username:
                server = _bot.get_server_by_id(server_id)
                if server and channel_name in server.channels:
                    hooks.append([server, server.channels.get(channel_name)])

        tweet = format._tweet(_exports, data)
        for server, channel in follows:
            self.events.on("send.stdout").call(target=channel,
                module_name="Tweets", server=server, message=tweet)
@utils.export("channelset", {"setting": "auto-tweet",
    "help": "Enable/disable automatically getting tweet info",
    "validate": utils.bool_or_none, "example": "on"})
class Module(ModuleManager.BaseModule):
    _stream = None
    def on_load(self):
        global _bot
        global _events
        global _exports
        _bot = self.bot
        _events = self.events
        _exports = self.exports
    def unload(self):
        self._dispose_stream()

    def _dispose_stream(self):
        if not self._stream == None:
            self._stream.disconnect()

    def _get_auth(self):
        auth = tweepy.OAuthHandler(self.bot.config["twitter-api-key"],
            self.bot.config["twitter-api-secret"])
        auth.set_access_token(self.bot.config["twitter-access-token"],
            self.bot.config["twitter-access-secret"])
        return auth
    def _get_api(self, auth):
        return tweepy.API(auth)

    def _from_id(self, tweet_id):
        return self._get_api(self._get_auth()).get_status(tweet_id)
    def _from_username(self, username):
        return self._get_api(self._get_auth()).user_timeline(
            screen_name=username, count=1)[0]

    def _start_stream(self):
        self._dispose_stream()

        auth = self._get_auth()
        self._stream = tweepy.Stream(auth=auth, listener=BitBotStreamListener)

        usernames = set([])
        for server_id, channel_name, value in _get_follows():
            usernames.add(value)

        self._stream.filter(follow=list(usernames), is_async=True)

    @utils.hook("received.command.tw", alias_of="tweet")
    @utils.hook("received.command.tweet")
    def tweet(self, event):
        """
        :help: Get/find a tweet
        :usage: [@username/URL/ID]
        """

        if event["args"]:
            target = event["args"]
        else:
            target = event["target"].buffer.find(REGEX_TWITTERURL)
            if target:
                target = target.message
        if target:
            url_match = re.search(REGEX_TWITTERURL, target)
            if url_match or target.isdigit():
                tweet_id = url_match.group(1) if url_match else target
                tweet = self._from_id(tweet_id)
            else:
                if target.startswith("@"):
                    target = target[1:]
                tweet = self._from_username(target)

            if tweet:
                tweet_str = format._tweet(self.exports, tweet)
                event["stdout"].write(tweet_str)
            else:
                event["stderr"].write("Invalid tweet identifiers provided")
        else:
            event["stderr"].write("No tweet provided to get information about")

    @utils.hook("command.regex", pattern=REGEX_TWITTERURL)
    def regex(self, event):
        """
        :command: tweet
        """
        if event["target"].get_setting("auto-tweet", False):
            event.eat()
            tweet_id = event["match"].group(1)
            tweet = self._from_id(tweet_id)
            if tweet:
                tweet_str = format._tweet(self.exports, tweet)
                event["stdout"].write(tweet_str)

