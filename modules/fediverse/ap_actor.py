import email.utils, urllib.parse
from bitbot import utils
from . import ap_security, ap_utils

class Actor(object):
    def __init__(self, url):
        self.url = url

        self.username = None
        self.display_name = None
        self.inbox = None
        self.outbox = None
        self.followers = None

    def load(self):
        response = ap_utils.activity_request(self.url)
        if response.code == 200:
            response = response.json()
            self.username = response["preferredUsername"]
            self.display_name = response.get("name", self.username)
            self.inbox = Inbox(response["inbox"])
            self.outbox = Outbox(response["outbox"])
            self.followers = response["followers"]
            return True
        return False

class Outbox(object):
    def __init__(self, url):
        self._url = url

    def load(self):
        outbox = ap_utils.activity_request(self._url).json()

        items = None
        if "first" in outbox:
            if type(outbox["first"]) == dict:
                # pleroma
                items = outbox["first"]["orderedItems"]
            else:
                # mastodon
                first = ap_utils.activity_request(outbox["first"]).json()
                items = first["orderedItems"]
        else:
            items = outbox["orderedItems"]
        return items

class Inbox(object):
    def __init__(self, url):
        self._url = url
    def send(self, sender, activity, private_key):
        now = email.utils.formatdate(timeval=None, localtime=False, usegmt=True)
        parts = urllib.parse.urlparse(self._url)
        headers = [
            ["Host", parts.netloc],
            ["Date", now]
        ]
        sign_headers = headers[:]
        sign_headers.insert(0, ["(request-target)", "post %s" % parts.path])
        signature = ap_security.signature(private_key, sign_headers)

        headers.append(["signature", signature])

        return ap_utils.activity_request(self._url, activity.format(sender),
            method="POST", headers=dict(headers)).json()

