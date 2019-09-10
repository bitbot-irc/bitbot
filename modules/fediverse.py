#--require-config tls-certificate

import urllib.parse
from src import ModuleManager, utils

HOSTMETA = "https://%s/.well-known/host-meta"
WEBFINGER_DEFAULT = "https://%s/.well-known/webfinger?resource={uri}"
WEBFINGER_HEADERS = {"Accept": "application/jrd+json"}

ACTIVITY_TYPE = "application/activity+json"
ACTIVITY_HEADERS = {"Accept": ("application/ld+json; "
    'profile="https://www.w3.org/ns/activitystreams"')}

def _parse_username(s):
    username, _, instance = s.rpartition("@")
    if username.startswith("@"):
        username = username[1:]
    if username and instance:
        return username, instance
    return None, None
def _format_username(username, instance):
    return "@%s@%s" % (username, instance)
def _setting_parse(s):
    username, instance = _parse_username(s)
    if username and instance:
        return _format_username(username, instance)
    return None

@utils.export("set", utils.FunctionSetting(_setting_parse, "fediverse",
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
            username, instance = _parse_username(account)

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
            self.log.debug("host-meta lookup failed for %s" % instance)
            webfinger_url = WEBFINGER_DEFAULT % instance
        webfinger_url = webfinger_url.replace("{uri}",
            "acct:%s@%s" % (username, instance))

        webfinger = utils.http.request(webfinger_url,
            headers=WEBFINGER_HEADERS, json=True)

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

    def _ap_self(self):
        our_username = self.bot.get_setting("fediverse", None)
        return _parse_username(our_username)
    def _ap_self_id(self, url_for, our_username):
        return "https://%s" % url_for("api", "ap-user", {"u": our_username})


    @utils.hook("api.get.ap-webfinger")
    @utils.kwarg("authenticated", False)
    def ap_webfinger(self, event):
        our_username, our_instance = self._ap_self()

        resource = event["params"].get("resource", None)
        if resource and resource.startswith("acct:"):
            request = resource.split(":", 1)[1]
            requested_username, requested_instance = _parse_username(request)

            if (requested_username == our_username and
                    requested_instance == our_instance):

                self_id = self._ap_self_id(event["url_for"], our_username)

                event["response"].content_type = "application/jrd+json"
                event["response"].write_json({
                    "aliases": [self_id],
                    "links": [{
                        "href": self_id,
                        "rel": "self",
                        "type": ACTIVITY_TYPE
                    }],
                    "subject": resource
                })
    @utils.hook("api.get.ap-user")
    @utils.kwarg("authenticated", False)
    def ap_user(self, event):
        our_username, our_instance = self._ap_self()
        username = event["params"].get("u", None)
        if username and username == our_username:
            self_id = self._ap_self_id(event["url_for"], our_username)
            inbox = event["url_for"]("api", "ap-inbox", {"u": our_username})

            cert_filename = self.bot.config["tls-certificate"]
            with open(cert_filename) as cert_file:
                cert = cert_file.read()

            event["response"].content_type = ("application/ld+json; "
                "profile=\"https://www.w3.org/ns/activitystreams\"")
            event["response"].write_json({
                "@context": [
                    "https://www.w3.org/ns/activitystreams",
                    "https://w3id.org/security/v1"
                ],
                "id": self_id,
                "type": "Person",
                "preferredUsername": our_username,
                "inbox": index,

                "publicKey": {
                    "id": "%s#key" % self_id,
                    "owner": self_id,
                    "publicKeyPem": cert
                }
            })
