from . import utils as ap_utils

class Activity(object):
    _type = ""
    def __init__(self, id, object):
        self._id = id
        self._object = object
    def format(self, actor):
        return {
            "@context": "https://www.w3.org/ns/activitystreams",
            "actor": actor.url,
            "id": self._id,
            "object": self._object,
            "type": self._type
        }

class Follow(Activity):
    _type = "Follow"
class Accept(Activity):
    _type = "Accept"

class Create(Activity):
    _type = "Create"

class Announce(Activity):
    _type = "Announce"
