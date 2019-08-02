import urllib.parse
from src import ModuleManager, utils

WEBFINGER = "https://%s/.well-known/webfinger"
WEBFINGER_HEADERS = {"Accept": "application/jrd+json"}

ACTIVITY_TYPE = "application/activity+json"
ACTIVITY_HEADERS = {"Accept": ("application/ld+json; "
    'profile="https://www.w3.org/ns/activitystreams"')}

class Module(ModuleManager.BaseModule):
    _name = "Fedi"

    @utils.hook("received.command.fediverse")
    @utils.hook("received.command.fedi", alias_of="fediverse")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("help", "Get someone's latest toot")
    @utils.kwarg("usage", "@<user>@<instance>")
    def fedi(self, event):
        full_username = event["args_split"][0].lstrip("@")
        username, _, instance = full_username.partition("@")
        if not username or not instance:
            raise utils.EventError("Please provide @<user>@<instance>")

        webfinger = utils.http.request(WEBFINGER % instance,
            headers=WEBFINGER_HEADERS,
            get_params={"resource": "acct:%s" % full_username},
            json=True)

        if webfinger.data:
            activity_url = None
            for link in webfinger.data["links"]:
                if link["type"] == ACTIVITY_TYPE:
                    activity_url = link["href"]
                    break

            if not activity_url:
                raise utils.EventError("Failed to find user activity feed")

            activity = utils.http.request(activity_url,
                headers=ACTIVITY_HEADERS, json=True)
            preferred_username = activity.data["preferredUsername"]
            outbox_url = activity.data["outbox"]

            outbox = utils.http.request(outbox_url, headers=ACTIVITY_HEADERS,
                json=True)
            items = None
            if "first" in outbox.data:
                if type(outbox.data["first"]) == dict:
                    items = outbox.data["first"]["orderedItems"]
                else:
                    first = utils.http.request(outbox.data["first"],
                        headers=ACTIVITY_HEADERS, json=True)
                    items = first.data["orderedItems"]
            else:
                items = outbox.data["orderedItems"]

            if items:
                first_item = items[0]
                if first_item["type"] == "Announce":
                    retoot_url = first_item["object"]
                    retoot_instance = urllib.parse.urlparse(retoot_url).hostname
                    retoot = utils.http.request(retoot_url,
                        headers=ACTIVITY_HEADERS, json=True)

                    original_tooter_url = retoot.data["attributedTo"]
                    original_tooter = utils.http.request(original_tooter_url,
                        headers=ACTIVITY_HEADERS, json=True)

                    retooted_user = "@%s@%s" % (
                        original_tooter.data["preferredUsername"],
                        retoot_instance)

                    shorturl = self.exports.get_one("shorturl")(
                        event["server"], retoot_url)
                    retoot_content = utils.http.strip_html(
                        retoot.data["content"])

                    event["stdout"].write("%s (boost %s): %s - %s" % (
                        preferred_username, retooted_user, retoot_content,
                        shorturl))

                elif first_item["type"] == "Create":
                    content = utils.http.strip_html(
                        first_item["object"]["content"])
                    url = first_item["object"]["id"]
                    shorturl = self.exports.get_one("shorturl")(
                        event["server"], url)

                    event["stdout"].write("%s: %s - %s" % (preferred_username,
                        content, shorturl))
