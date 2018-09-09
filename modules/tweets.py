# --require-config twitter-api-key
# --require-config twitter-api-secret
# --require-config twitter-access-token
# --require-config twitter-access-secret

import datetime, re, time, traceback
import twitter
import Utils

REGEX_TWITTERURL = re.compile(
    "https?://(?:www\.)?twitter.com/[^/]+/status/(\d+)", re.I)


class Module(object):

    def __init__(self, bot, events, exports):
        self.bot = bot
        self.bitly_is_enabled = "bitly" in self.bot.modules.modules

        events.on("received").on("command").on("tweet", "tw"
                                               ).hook(self.tweet,
                                                      help="Find a tweet",
                                                      usage="[@username/URL/ID]")

    def make_timestamp(self, s):
        seconds_since = time.time() - datetime.datetime.strptime(s,
                                                                 "%a %b %d "
                                                                 "%H:%M:%S %z "
                                                                 "%Y").timestamp()
        since, unit = Utils.time_unit(seconds_since)
        return "%s %s ago" % (since, unit)

    def tweet(self, event):
        api_key = self.bot.config["twitter-api-key"]
        api_secret = self.bot.config["twitter-api-secret"]
        access_token = self.bot.config["twitter-access-token"]
        access_secret = self.bot.config["twitter-access-secret"]

        if event["args"]:
            target = event["args"]
        else:
            target = event["buffer"].find(REGEX_TWITTERURL)
            if target:
                target = target.message
        if target:
            twitter_object = twitter.Twitter(auth=twitter.OAuth(
                access_token, access_secret, api_key, api_secret))
            url_match = re.search(REGEX_TWITTERURL, target)
            if url_match or target.isdigit():
                tweet_id = url_match.group(1) if url_match else target
                try:
                    tweet = twitter_object.statuses.show(id=tweet_id)
                except:
                    traceback.print_exc()
                    tweet = None
            else:
                if target.startswith("@"):
                    taret = target[1:]
                try:
                    tweet = twitter_object.statuses.user_timeline(
                        screen_name=target, count=1)[0]
                except:
                    traceback.print_exc()
                    tweet = None
            if tweet:
                linked_id = tweet["id"]
                username = "@%s" % tweet["user"]["screen_name"]

                bitly_link = ""
                if self.bitly_is_enabled:
                    bitly = self.bot.modules.modules["bitly"]
                    chopped_uname = username[1:]
                    tweet_link = "https://twitter.com/%s/status/%s" % (
                        chopped_uname, linked_id)

                    bitly_link = " -- " + bitly.shortlink(tweet_link)

                if "retweeted_status" in tweet:
                    original_username = "@%s" % tweet["retweeted_status"
                    ]["user"]["screen_name"]
                    original_text = tweet["retweeted_status"]["text"]
                    retweet_timestamp = self.make_timestamp(tweet[
                                                                "created_at"])
                    original_timestamp = self.make_timestamp(tweet[
                                                                 "retweeted_status"][
                                                                 "created_at"])
                    event["stdout"].write(
                        "(%s (%s) retweeted %s (%s)) %s %s" % (
                            username, retweet_timestamp,
                            original_username, original_timestamp,
                            original_text,
                            bitly_link))
                else:
                    event["stdout"].write("(%s, %s) %s %s" % (username,
                                                              self.make_timestamp(
                                                                  tweet[
                                                                      "created_at"]),
                                                              tweet["text"],
                                                              bitly_link)
                                          )
            else:
                event["stderr"].write("Invalid tweet identifiers provided")
        else:
            event["stderr"].write("No tweet provided to get information about")
