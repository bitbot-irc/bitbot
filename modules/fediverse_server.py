#--require-config tls-certificate

import urllib.parse
from src import ModuleManager, utils

ACTIVITY_TYPE = "application/activity+json"
ACTIVITY_TYPE = ("application/ld+json; "
    "profile=\"https://www.w3.org/ns/activitystreams\"")
WEBFINGER_TYPE = "application/jrd+json"


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

@utils.export("botset", utils.FunctionSetting(_setting_parse, "fediverse",
    help="Set the bot's fediverse server account",
    example="@gargron@mastodon.social"))
class Module(ModuleManager.BaseModule):
    _name = "Fedi"

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
        if resource.startswith("acct:"):
            resource = resource.split(":", 1)[1]

        if resource:
            requested_username, requested_instance = _parse_username(resource)

            if (requested_username == our_username and
                    requested_instance == our_instance):

                self_id = self._ap_self_id(event["url_for"], our_username)

                event["response"].content_type = WEBFINGER_TYPE
                event["response"].write_json({
                    "aliases": [self_id],
                    "links": [{
                        "href": self_id,
                        "rel": "self",
                        "type": ACTIVITY_TYPE
                    }],
                    "subject": resource
                })
            else:
                event["response"].code = 404
        else:
            event["response"].code = 400

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
                cert = cert_file.read().strip()

            event["response"].content_type = ACTIVITY_TYPE
            event["response"].write_json({
                "@context": [
                    "https://www.w3.org/ns/activitystreams",
                    "https://w3id.org/security/v1"
                ],
                "id": self_id,
                "type": "Person",
                "preferredUsername": our_username,
                "inbox": inbox,
                "publicKey": {
                    "id": "%s#key" % self_id,
                    "owner": self_id,
                    "publicKeyPem": cert
                }
            })
