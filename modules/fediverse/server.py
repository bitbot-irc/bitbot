#--require-config tls-certificate

import base64, binascii, os, urllib.parse
from src import ModuleManager, utils

from . import actor as ap_actor
from . import activities as ap_activities
from . import security as ap_security

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
    @utils.kwarg("permission", "fediverse")
    def toot(self, event):
        activity_id = self._make_activity(event["args"])
        event["stdout"].write("Sent toot %s" % activity_id)

    @utils.hook("received.command.fedifollow")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("permission", "fediverse")
    def fedi_follow(self, event):
        pass

    def _toot(self, activity_id):
        our_username, our_instance = self._ap_self()
        content, timestamp = self.bot.get_setting(
            "ap-activity-%s" % activity_id)
        url_for = self.exports.get_one("url-for")
        self_id = self._ap_self_url(url_for, our_username)
        activity_url = self._ap_activity_url(url_for, activity_id)

        object = {
            "id": activity_url,
            "type": "Note",
            "published": timestamp,
            "attributedTo": self_id,
            "content": content,
            "to": "https://www.w3.org/ns/activitystreams#Public"
        }
        activity = ap_activities.Create(activity_url, object)

        private_key = self._private_key()

        for actor_url in self._get_actors():
            actor = ap_actor.Actor(actor_url)
            actor.load()
            actor.inbox.send(activity, private_key)

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

                event["response"].content_type = consts.JRD_TYPE
                event["response"].write_json({
                    "aliases": [self_id],
                    "links": [{
                        "href": self_id,
                        "rel": "self",
                        "type": consts.ACTIVITY_TYPE
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

            event["response"].content_type = consts.LD_TYPE
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

            event["response"].content_type = consts.LD_TYPE
            event["response"].write_json({
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": outbox,
                "orderedItems": activities,
                "totalItems": len(activities),
                "type": "OrderedCollection"
            })

        else:
            event["response"].code = 404

    def _private_key(self):
        id = self._ap_keyid_url(url_for, our_username)
        filename = security.private_key(self.bot.config["tls-certificate"])
        return ap_security.PrivateKey(filename, id)

    @utils.hook("api.post.ap-inbox")
    @utils.kwarg("authenticated", False)
    def ap_inbox(self, event):
        data = json.loads(event["data"])
        self_id = self._ap_self_url(event["url_for"], our_username)

        if data["type"] == "Follow":
            if data["object"] == self_id:
                new_follower = data["actor"]
                followers = set(self.bot.get_setting("fediverse-followers", []))
                if not new_follower in followers:
                    followers.add(new_follower)

                    private_key = self._private_key()
                    actor = ap_actor.Actor(new_follower)
                    accept = ap_activities.Accept(data["id"], data)
                    actor.inbox.send(accept, private_key)

                    follow_id = "data:%s" % str(uuid.uuid4())
                    follow = ap_activities.Follow(follow_id, self_id)
                    actor.inbox.send(follow, private_key)
            else:
                event["response"].code = 404
