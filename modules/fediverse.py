import urllib.parse
from src import ModuleManager, utils

HOSTMETA = "https://%s/.well-known/host-meta"
WEBFINGER_HEADERS = {"Accept": "application/jrd+json"}

ACTIVITY_TYPE = "application/activity+json"
ACTIVITY_HEADERS = {"Accept": ("application/ld+json; "
    'profile="https://www.w3.org/ns/activitystreams"')}

def _parse_username(s):
    username, _, instance = s.partition("@")
    if username.startswith("@"):
        username = username[1:]
    if username and instance:
        return "@%s@%s" % (username, instance)
    return None

@utils.export("set", utils.FunctionSetting(_parse_username, "fediverse",
    help="Set your fediverse account", example="@gargron@mastodon.social"))
class Module(ModuleManager.BaseModule):
    _name = "Fedi"

    @utils.hook("received.command.fediverse")
    @utils.hook("received.command.fedi", alias_of="fediverse")
    @utils.kwarg("help", "Get someone's latest toot")
    @utils.kwarg("usage", "@<user>@<instance>")
    def fedi(self, event):
        account = None
        if not event["args"]:
            account = event["user"].get_setting("fediverse", None)
        elif not "@" in event["args"]:
            target = event["args_split"][0]
            if event["server"].has_user_id(target):
                target_user = event["server"].get_user(target)
                account = target_user.get_setting("fediverse", None)
        else:
            account = event["args_split"][0]

        username = None
        instance = None
        if account:
            account = account.lstrip("@")
            username, _, instance = account.partition("@")

        if not username or not instance:
            raise utils.EventError("Please provide @<user>@<instance>")

        hostmeta = utils.http.request(HOSTMETA % instance,
            soup=True, check_content_type=False)
        webfinger_url = None
        for item in hostmeta.data.find_all("link"):
            if item["rel"] and item["rel"][0] == "lrdd":
                webfinger_url = item["template"]
                break

        if webfinger_url == None:
            raise utils.EventError("host-meta lookup failed for %s" %
                instance)
        webfinger_url = webfinger_url.replace("{uri}", "acct:%s" % account)

        webfinger = utils.http.request(webfinger_url,
            headers=WEBFINGER_HEADERS,
            get_params={"resource": "acct:%s" % account},
            json=True)

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
                # pleroma
                items = outbox.data["first"]["orderedItems"]
            else:
                # mastodon
                first = utils.http.request(outbox.data["first"],
                    headers=ACTIVITY_HEADERS, json=True)
                items = first.data["orderedItems"]
        else:
            items = outbox.data["orderedItems"]

        if not items:
            raise utils.EventError("No toots found")

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
