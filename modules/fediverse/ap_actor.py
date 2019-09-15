import email.utils
from src import utils
from . import ap_utils

class Actor(object):
    def __init__(self, url):
        self.url = url

        self.username = None
        self.inbox = None
        self.outbox = None

    def load(self):
        data = ap_utils.activity_request(self.url)
        self.username = data["preferredUsername"]
        self.inbox = Inbox(data["inbox"])
        self.outbox = Outbox(data["outbox"])

class Outbox(object):
    def __init__(self, url):
        self._url = url

    def load(self):
        outbox = ap_utils.activity_request(self._url)

        items = None
        if "first" in outbox:
            if type(outbox["first"]) == dict:
                # pleroma
                items = outbox["first"]["orderedItems"]
            else:
                # mastodon
                first = ap_utils.activity_request(outbox["first"])
                items = first["orderedItems"]
        else:
            items = outbox["orderedItems"]
        return items

class Inbox(object):
    def __init__(self, url):
        self._url = url
    def send(activity, private_key):
        now = email.utils.formatdate(timeval=None, localtime=False, usegmt=True)
        parts = urllib.parse.urlparse(self._url)
        headers = [
            ["host", parts.netloc],
            ["date", now]
        ]
        sign_headers = headers[:]
        sign_headers.insert(0, ["(request-target)", "post %s" % parts.path])
        signature = security.signature(private_key.key, sign_headers)

        return ap_utils.request(self._url, activity.format(self),
            method="POST", private_key=private_key)

