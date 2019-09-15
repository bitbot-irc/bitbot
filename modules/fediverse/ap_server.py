import base64, binascii, os, urllib.parse
from src import ModuleManager, utils

from . import ap_activities, ap_actor, ap_security, ap_utils

ACTIVITY_SETTING_PREFIX = "ap-activity-"

class Server(object):
    def __init__(self, bot, username, instance):
        self.bot = bot
        self.username = username
        self.instance = instance

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

    def _toot(self, activity_id):
        content, timestamp = self.bot.get_setting(
            "ap-activity-%s" % activity_id)
        url_for = self.exports.get_one("url-for")
        self_id = self._ap_self_url(url_for)
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

    def _ap_url(self, url_for, fragment, kwargs):
        return "https://%s" % url_for("api", fragment, kwargs)
    def _ap_self_url(self, url_for):
        return self._ap_url(url_for, "ap-user", {"u": self.username})
    def _ap_inbox_url(self, url_for):
        return self._ap_url(url_for, "ap-inbox", {"u": self.username})
    def _ap_outbox_url(self, url_for):
        return self._ap_url(url_for, "ap-outbox", {"u": self.username})
    def _ap_activity_url(self, url_for, activity_id):
        return self._ap_url(url_for, "ap-activity", {"a": activity_id})
    def _ap_keyid_url(self, url_for):
        return "%s#key" % self._ap_self_url(url_for)

    def ap_webfinger(self, event):
        resource = event["params"].get("resource", None)
        if resource.startswith("acct:"):
            resource = resource.split(":", 1)[1]

        if resource:
            requested_username, requested_instance = ap_utils.split_username(
                resource)

            if (requested_username == self.username and
                    requested_instance == self.instance):

                self_id = self._ap_self_url(event["url_for"], self.username)

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

    def ap_user(self, event):
        username = event["params"].get("u", None)

        if username and username == self.username:
            self_id = self._ap_self_url(event["url_for"])
            inbox = self._ap_inbox_url(event["url_for"])
            outbox = self._ap_outbox_url(event["url_for"])

            cert_filename = self.bot.config["tls-certificate"]
            with open(cert_filename) as cert_file:
                cert = cert_file.read().strip()

            event["response"].content_type = consts.LD_TYPE
            event["response"].write_json({
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": self_id, "url": self_id,
                "type": "Person",
                "summary": "beep boop",
                "preferredUsername": self.username, "name": self.username,
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

    def ap_outbox(self, event):
        username = event["params"].get("u", None)
        if username and username == self.username:
            self_id = self._ap_self_url(event["url_for"])
            outbox = self._ap_outbox_url(event["url_for"])

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
        id = self._ap_keyid_url(url_for)
        filename = security.private_key(self.bot.config["tls-certificate"])
        return ap_security.PrivateKey(filename, id)

    def ap_inbox(self, event):
        data = json.loads(event["data"])
        self_id = self._ap_self_url(event["url_for"])

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
