#--require-config twitter-api-key
#--require-config twitter-api-secret
#--require-config twitter-access-token
#--require-config twitter-access-secret

import datetime, html, re, time, traceback
import twitter
from src import ModuleManager, utils

REGEX_TWITTERURL = re.compile(
    "https?://(?:www\.)?twitter.com/[^/]+/status/(\d+)", re.I)

@utils.export("channelset", {"setting": "auto-tweet",
    "help": "Enable/disable automatically getting tweet info",
    "validate": utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    _name = "Twitter"

    def make_timestamp(self, s):
        seconds_since = time.time() - datetime.datetime.strptime(s,
            "%a %b %d %H:%M:%S %z %Y").timestamp()
        since, unit = utils.time_unit(seconds_since)
        return "%s %s ago" % (since, unit)

    def _get_api(self):
        api_key = self.bot.config["twitter-api-key"]
        api_secret = self.bot.config["twitter-api-secret"]
        access_token = self.bot.config["twitter-access-token"]
        access_secret = self.bot.config["twitter-access-secret"]
        return twitter.Twitter(auth=twitter.OAuth(
            access_token, access_secret, api_key, api_secret))

    def _from_id(self, tweet_id):
        api = self._get_api()
        try:
            return api.statuses.show(id=tweet_id)
        except:
            traceback.print_exc()

    def _format_tweet(self, tweet):
        linked_id = tweet["id"]
        username = tweet["user"]["screen_name"]

        tweet_link = "https://twitter.com/%s/status/%s" % (username,
            linked_id)

        short_url = self.exports.get_one("shortlink")(tweet_link)
        short_url = " - %s" % short_url if short_url else ""

        if "retweeted_status" in tweet:
            original_username = "@%s" % tweet["retweeted_status"
                ]["user"]["screen_name"]
            original_text = tweet["retweeted_status"]["text"]
            retweet_timestamp = self.make_timestamp(tweet[
                "created_at"])
            original_timestamp = self.make_timestamp(tweet[
                "retweeted_status"]["created_at"])
            return "(@%s (%s) retweeted %s (%s)) %s%s" % (
                username, retweet_timestamp, original_username,
                original_timestamp, html.unescape(original_text),
                short_url)
        else:
            return "(@%s, %s) %s%s" % (username,
                self.make_timestamp(tweet["created_at"]),
                html.unescape(tweet["text"]), short_url)

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
                api = self._get_api()
                try:
                    tweet = api.statuses.user_timeline(
                        screen_name=target, count=1)[0]
                except:
                    traceback.print_exc()
                    tweet = None
            if tweet:
                tweet_str = self._format_tweet(tweet)
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
                tweet_str = self._format_tweet(tweet)
                event["stdout"].write(tweet_str)
