#--depends-on commands
#--depends-on permissions
#--depends-on shorturl
#--require-config twitter-api-key
#--require-config twitter-api-secret
#--require-config twitter-access-token
#--require-config twitter-access-secret

import json, re, threading
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
        _bot.trigger(lambda: self._on_status(status))
    def _on_status(self, status):
        given_username = status.user.screen_name.lower()

        follows = []
        for server_id, channel_name, value in _get_follows():
            for username in value:
                if username.lower() == given_username:
                    server = _bot.get_server_by_id(server_id)
                    if server and channel_name in server.channels:
                        follows.append([server, server.channels.get(channel_name)])

        for server, channel in follows:
            tweet = format._tweet(_exports, server, status)
            _events.on("send.stdout").call(target=channel,
                module_name="Tweets", server=server, message=tweet)

@utils.export("channelset", {"setting": "auto-tweet",
    "help": "Enable/disable automatically getting tweet info",
    "validate": utils.bool_or_none, "example": "on"})
class Module(ModuleManager.BaseModule):
    _stream = None
    def on_load(self):
        self._thread = None

        global _bot
        global _events
        global _exports
        _bot = self.bot
        _events = self.events
        _exports = self.exports
        self._start_stream()

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

        usernames = set([])
        for server_id, channel_name, value in _get_follows():
            for username in value:
                usernames.add(username)
        if not usernames:
            return False

        auth = self._get_auth()
        api = self._get_api(auth)

        user_ids = []
        for username in usernames:
            user_ids.append(str(api.get_user(screen_name=username).id))

        self._stream = tweepy.Stream(auth=auth, listener=BitBotStreamListener())

        self._thread = threading.Thread(
            target=lambda: self._stream.filter(follow=user_ids))
        self._thread.daemon = True
        self._thread.start()
        return True

    @utils.hook("received.command.tfollow", min_args=2, channel_only=True)
    def tfollow(self, event):
        """
        :help: Stream tweets from a given account to the current channel
        :usage: add|remove @<username>
        :permission: twitter-follow
        """
        username = event["args_split"][1]
        if username.startswith("@"):
            username = username[1:]

        subcommand = event["args_split"][0].lower()
        follows = event["target"].get_setting("twitter-follow", [])
        action = None

        if subcommand == "add":
            action = "followed"
            if username in follows:
                raise utils.EventError("Already following %s" % username)
            follows.append(username)
        elif subcommand == "remove":
            action = "unfollowed"
            if not username in follows:
                raise utils.EventError("Not following %s" % username)
            follows.remove(username)
        else:
            raise utils.EventError("Unknown subcommand")

        event["target"].set_setting("twitter-follow", follows)
        self._start_stream()
        event["stdout"].write("%s @%s" % (action.title(), username))

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
                tweet_str = format._tweet(self.exports, event["server"], tweet)
                event["stdout"].write(tweet_str)
            else:
                event["stderr"].write("Invalid tweet identifiers provided")
        else:
            event["stderr"].write("No tweet provided to get information about")

    @utils.hook("command.regex")
    @utils.kwarg("ignore_action", False)
    @utils.kwarg("command", "tweet")
    @utils.kwarg("pattern", REGEX_TWITTERURL)
    def regex(self, event):
        if event["target"].get_setting("auto-tweet", False):
            event.eat()
            tweet_id = event["match"].group(1)
            tweet = self._from_id(tweet_id)
            if tweet:
                tweet_str = format._tweet(self.exports, event["server"], tweet)
                event["stdout"].write(tweet_str)

