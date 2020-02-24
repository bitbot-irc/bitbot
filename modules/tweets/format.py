import datetime, html, time
from src import utils

def _timestamp(dt):
    seconds_since = time.time()-dt.timestamp()
    timestamp = utils.datetime.format.to_pretty_since(
        seconds_since, max_units=2)
    return "%s ago" % timestamp

def _normalise(tweet):
    return html.unescape(utils.parse.line_normalise(tweet))

def _tweet(exports, server, tweet, from_url):
    linked_id = tweet.id
    username = tweet.user.screen_name

    verified = ""
    if tweet.user.verified:
        verified = " %s" % utils.irc.color("✓", utils.consts.LIGHTBLUE)

    tweet_link = "https://twitter.com/%s/status/%s" % (username,
        linked_id)

    short_url = ""
    if not from_url:
        short_url = exports.get_one("shorturl")(server, tweet_link)
        short_url = " - %s" % short_url if short_url else ""
    created_at = _timestamp(tweet.created_at)

    # having to use hasattr here is nasty.
    if hasattr(tweet, "retweeted_status"):
        original_username = tweet.retweeted_status.user.screen_name
        original_text = tweet.retweeted_status.full_text
        original_timestamp = _timestamp(tweet.retweeted_status.created_at)
        return "(@%s%s (%s) retweeted @%s (%s)) %s%s" % (username, verified,
            created_at, original_username, original_timestamp,
            _normalise(original_text), short_url)
    else:
        return "(@%s%s, %s) %s%s" % (username, verified, created_at,
            _normalise(tweet.full_text), short_url)

