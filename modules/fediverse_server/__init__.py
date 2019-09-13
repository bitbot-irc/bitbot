#--require-config tls-certificate

import base64, binascii, os, urllib.parse
from src import ModuleManager, utils

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

LD_TYPE = ("application/ld+json; "
    "profile=\"https://www.w3.org/ns/activitystreams\"")
JRD_TYPE = "application/jrd+json"
ACTIVITY_TYPE = "application/activity+json"

ACTIVITY_SETTING_PREFIX = "ap-activity-"

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

    def _random_id(self):
        return binascii.hexlify(os.urandom(3)).decode("ascii")

    def _get_activities(self):
        activities = []
        for setting, (content, timestamp) in self.bot.find_settings_prefix(
                ACTIVITY_SETTING_PREFIX):
            activity_id = setting.replace(ACTIVITY_SETTING_PREFIX, "", 1)
            activities.append([activity_id, content, timestamp])
        return activities
    def _make_activity(self, content):
        timestamp = utils.iso8601_format_now()
        activity_id = self._random_id()
        self.bot.set_setting("ap-activity-%s" % activity_id,
            [content, timestamp])
        return activity_id

    @utils.hook("received.command.toot")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("permission", "toot")
    def toot(self, event):
        activity_id = self._make_activity(event["args"])
        event["stdout"].write("Sent toot %s" % activity_id)

    def _federate_activity(self, activity_id, content, timestamp):

        message = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Announce",
            "to": [],
            "actor": "",
            "object": ""
        }


    def _federate(self, data):
        our_username, our_instance = self._ap_self()
        key_id = self._ap_keyid_url(url_for, our_username)
        now = email.utils.formatdate(timeval=None, localtime=False, usegmt=True)
        url_for = self.exports.get_one("url-for")

        key = security.private_key(self.bot.config["tls-certificate"])

        for inbox in self._get_inboxes():
            parts = urllib.parse.urlparse(inbox)
            headers = [
                ["host", parts.netloc],
                ["date", now]
            ]
            sign_headers = headers[:]
            sign_headers.insert(0, ["(request-target)", "post %s" % parts.path])

            signature = security.signature(key, key_id, sign_headers)
            data = ""
            request = utils.http.Request(inbox, data=data, headers=headers,
                content_type=ACTIVITY_TYPE, useragent="BitBot Fediverse")
            utils.http.request()

    def _ap_self(self):
        our_username = self.bot.get_setting("fediverse", None)
        return _parse_username(our_username)

    def _ap_url(self, url_for, fragment, kwargs):
        return "https://%s" % url_for("api", fragment, kwargs)
    def _ap_self_url(self, url_for, our_username):
        return self._ap_url(url_for, "ap-user", {"u": our_username})
    def _ap_inbox_url(self, url_for, our_username):
        return self._ap_url(url_for, "ap-inbox", {"u": our_username})
    def _ap_outbox_url(self, url_for, our_username):
        return self._ap_url(url_for, "ap-outbox", {"u": our_username})
    def _ap_activity_url(self, url_for, activity_id):
        return self._ap_url(url_for, "ap-activity", {"a": activity_id})
    def _ap_keyid_url(self, url_for, our_username):
        return "%s#key" % self._ap_self_url(url_for, our_username)

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

                self_id = self._ap_self_url(event["url_for"], our_username)

                event["response"].content_type = JRD_TYPE
                event["response"].write_json({
                    "aliases": [self_id],
                    "links": [{
                        "href": self_id,
                        "rel": "self",
                        "type": ACTIVITY_TYPE
                    }],
                    "subject": "acct:%s" % resource
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
            self_id = self._ap_self_url(event["url_for"], our_username)
            inbox = self._ap_inbox_url(event["url_for"], our_username)
            outbox = self._ap_outbox_url(event["url_for"], our_username)

            cert_filename = self.bot.config["tls-certificate"]
            with open(cert_filename) as cert_file:
                cert = cert_file.read().strip()

            event["response"].content_type = LD_TYPE
            event["response"].write_json({
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": self_id, "url": self_id,
                "type": "Person",
                "summary": "beep boop",
                "preferredUsername": our_username, "name": our_username,
                "inbox": inbox,
                "outbox": outbox,
                "publicKey": {
                    "id": "%s#key" % self_id,
                    "owner": self_id,
                    "publicKeyPem": cert
                }
            })
        else:
            event["response"].code = 404

    def _prepare_activity(self, url_for, self_id, activity_id, content,
            timestamp):
        activity_url = self._ap_activity_url(url_for, activity_id)
        context = "data:%s" % activity_id
        return activity_url, {
            "attributedTo": self_id,
            "content": content,
            "conversation": context, "context": context,
            "id": activity_url, "url": activity_url,
            "published": timestamp,
            "summary": "", # content warning here
            "to": "https://www.w3.org/ns/activitystreams#Public",
            "type": "Note",
        }

    @utils.hook("api.get.ap-outbox")
    @utils.kwarg("authenticated", False)
    def ap_outbox(self, event):
        our_username, our_instance = self._ap_self()
        username = event["params"].get("u", None)
        if username and username == our_username:
            self_id = self._ap_self_url(event["url_for"], our_username)
            outbox = self._ap_outbox_url(event["url_for"], our_username)

            activities = []
            for activity_id, content, timestamp in self._get_activities():
                activity_url, activity_object = self._prepare_activity(
                    event["url_for"], self_id, activity_id, content, timestamp)
                activities.append({
                    "actor": self_id,
                    "id": activity_url,
                    "object": activity_object,
                    "published": timestamp,
                    "to": "https://www.w3.org/ns/activitystreams#Public",
                    "type": "Create"
                })

            event["response"].content_type = LD_TYPE
            event["response"].write_json({
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": outbox,
                "orderedItems": activities,
                "totalItems": len(activities),
                "type": "OrderedCollection"
            })

        else:
            event["response"].code = 404

