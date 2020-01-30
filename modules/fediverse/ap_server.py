import base64, binascii, json, os, queue, threading, urllib.parse, uuid
from src import ModuleManager, utils

from . import ap_activities, ap_actor, ap_security, ap_utils

ACTIVITY_SETTING_PREFIX = "ap-activity-"

class Server(object):
    def __init__(self, bot, exports, username, instance):
        self.bot = bot
        self.exports = exports
        self.username = username
        self.instance = instance

        url_for = self.exports.get_one("url-for")

        key_id = self._ap_keyid_url(url_for)
        private_key = ap_security.PrivateKey(self.bot.config["tls-key"], key_id)

        self_id = self._ap_self_url(url_for)
        our_actor = ap_actor.Actor(self_id)

        del url_for

        self._request_queue = queue.Queue()
        self._request_thread = threading.Thread(target=self._request_loop,
            args=(private_key, our_actor))
        self._request_thread.daemon = True
        self._request_thread.start()

    def _request_loop(self, private_key, our_actor):

        while True:
            obj = self._request_queue.get()
            if obj == "kill":
                break
            else:
                actor, activity = obj
                actor.inbox.send(our_actor, activity, private_key)

    def unload(self):
        self._request_queue.put("kill")

    def _random_id(self):
        return binascii.hexlify(os.urandom(3)).decode("ascii")

    def _get_activities(self):
        activities = []
        for setting, (content, timestamp) in self.bot.find_settings(
                prefix=ACTIVITY_SETTING_PREFIX):
            activity_id = setting.replace(ACTIVITY_SETTING_PREFIX, "", 1)
            activities.append([activity_id, content, timestamp])
        return activities
    def _make_activity(self, content):
        timestamp = utils.datetime.format.iso8601_now()
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

    def _ap_url(self, url_for, fragment, arg):
        return "https://%s" % url_for("api", fragment, args=[arg])
    def _ap_self_url(self, url_for):
        return self._ap_url(url_for, "ap-user", self.username)
    def _ap_inbox_url(self, url_for):
        return self._ap_url(url_for, "ap-inbox", self.username)
    def _ap_outbox_url(self, url_for):
        return self._ap_url(url_for, "ap-outbox", self.username)
    def _ap_activity_url(self, url_for, activity_id):
        return self._ap_url(url_for, "ap-activity", activity_id)
    def _ap_keyid_url(self, url_for):
        return "%s#key" % self._ap_self_url(url_for)
    def _ap_uuid_url(self, url_for):
        return self._ap_url(url_for, "ap-id", str(uuid.uuid4()))

    def ap_webfinger(self, event):
        resource = event["params"].get("resource", None)
        if resource.startswith("acct:"):
            resource = resource.split(":", 1)[1]

        if resource:
            requested_username, requested_instance = ap_utils.split_username(
                resource)

            if (requested_username == self.username and
                    requested_instance == self.instance):

                self_id = self._ap_self_url(event["url_for"])

                event["response"].content_type = ap_utils.JRD_TYPE
                event["response"].write_json({
                    "aliases": [self_id],
                    "links": [{
                        "href": self_id,
                        "rel": "self",
                        "type": ap_utils.ACTIVITY_TYPE
                    }],
                    "subject": "acct:%s" % resource
                })
            else:
                event["response"].code = 404
        else:
            event["response"].code = 400

    def _get_arg(self, args):
        return (args or [None])[0]

    def ap_user(self, event):
        username = self._get_arg(event["args"])

        if username and username == self.username:
            self_id = self._ap_self_url(event["url_for"])
            inbox = self._ap_inbox_url(event["url_for"])
            outbox = self._ap_outbox_url(event["url_for"])

            cert_filename = self.bot.config["tls-certificate"]
            pubkey = ap_security.public_key(cert_filename)

            event["response"].content_type = ap_utils.LD_TYPE
            event["response"].write_json({
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": self_id, "url": self_id,
                "type": "Service",
                "summary": "beep boop",
                "preferredUsername": self.username, "name": self.username,
                "inbox": inbox,
                "outbox": outbox,
                "publicKey": {
                    "id": "%s#key" % self_id,
                    "owner": self_id,
                    "publicKeyPem": pubkey
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
        username = self._get_arg(event["args"])

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

            event["response"].content_type = ap_utils.LD_TYPE
            event["response"].write_json({
                "@context": "https://www.w3.org/ns/activitystreams",
                "id": outbox,
                "orderedItems": activities,
                "totalItems": len(activities),
                "type": "OrderedCollection"
            })

        else:
            event["response"].code = 404

    def _private_key(self, id):
        filename = self.bot.config["tls-key"]
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

                    actor = ap_actor.Actor(new_follower)
                    actor.load()
                    accept = ap_activities.Accept(
                        self._ap_uuid_url(event["url_for"]), data)
                    self._request_queue.put([actor, accept])

                    follow = ap_activities.Follow(
                        self._ap_uuid_url(event["url_for"]), actor.url)
                    self._request_queue.put([actor, follow])
            else:
                event["response"].code = 404
