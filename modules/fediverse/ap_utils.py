import os.path, urllib.parse
import bs4
from src import IRCBot, utils
from . import ap_actor

LD_TYPE = ("application/ld+json; "
    "profile=\"https://www.w3.org/ns/activitystreams\"")
JRD_TYPE = "application/jrd+json"
ACTIVITY_TYPE = "application/activity+json"

def split_username(s):
    if s[0] == "@":
        s = s[1:]
    username, _, instance = s.partition("@")
    if username and instance:
        return username, instance
    return None, None

def activity_request(url, data=None, method="GET", type=ACTIVITY_TYPE,
        headers={}):
    content_type = None

    if method == "POST":
        content_type = type
    else:
        headers = {"Accept": type}

    request = utils.http.Request(url, headers=headers,
        content_type=content_type, post_data=data, method=method, json=True,
        json_body=True, fallback_encoding="utf8")
    return utils.http.request(request)

HOSTMETA_TEMPLATE = "https://%s/.well-known/host-meta"
WEBFINGER_TEMPLATE = "https://%s/.well-known/webfinger?resource={uri}"

class FindActorException(Exception):
    pass

def find_actor(username, instance):
    hostmeta = HOSTMETA_TEMPLATE % instance
    hostmeta_request = utils.http.Request(HOSTMETA_TEMPLATE % instance,
        parse=True, check_content_type=False)
    try:
        hostmeta = utils.http.request(hostmeta_request)
    except:
        raise FindActorException("Failed to get host-meta for %s" % instance)

    webfinger_url = None
    if hostmeta.code == 200:
        for item in hostmeta.data.find_all("link"):
            if item["rel"] and item["rel"][0] == "lrdd":
                webfinger_url = item["template"]
                break

    if not webfinger_url:
        webfinger_url = WEBFINGER_TEMPLATE % instance
    webfinger_url = webfinger_url.replace("{uri}",
        "acct:%s@%s" % (username, instance), 1)

    try:
        webfinger = activity_request(webfinger_url, type=JRD_TYPE)
    except:
        raise FindActorException("Failed to get webfinger for %s" % instance)

    actor_url = None
    if webfinger.code == 200:
        for link in webfinger.data["links"]:
            if link["type"] == ACTIVITY_TYPE:
                return link["href"]
    else:
        raise FindActorException("Could not find user @%s@%s" %
            (username, instance))

KNOWN_TAGS = ["p", "br"]

def _line(item):
    if type(item) == bs4.element.Tag:
        if item.name == "p":
            out = ""
            for subitem in item.children:
                out += _line(subitem)
            return "\n%s\n" % out
        elif item.name == "br":
            return "\n"
    else:
        return str(item)

def _normalise_note(content):
    soup = bs4.BeautifulSoup(content, "lxml").body
    lines = []
    for element in soup.find_all():
        if not element.name in KNOWN_TAGS:
            if element.text.strip() == "":
                element.decompose()
            else:
                element.unwrap()

    out = ""
    for element in soup.children:
        out += _line(element)

    return utils.parse.line_normalise(out)

def _content(note):
    content = note.get("content", None)
    attachment = note.get("attachment", [])

    if note.get("content", None):
        return _normalise_note(content)
    elif attachment:
        type = attachment[0]["mediaType"].split("/", 1)[0]
        filename = os.path.basename(attachment[0]["url"])

        extension = None
        if "." in filename:
            filename, extension = filename.rsplit(".", 1)
        if len(filename) > 20:
            filename = "%s[...]" % filename[:20]

        if extension:
            filename = "%s.%s" % (filename, extension)
        else:
            filename = "%s: %s" % (type, filename)

        return "<%s>" % filename

def format_note(actor, note, type="Create"):
    if type == "Announce":
        retoot_url = note
        retoot_instance = urllib.parse.urlparse(retoot_url).hostname
        retoot = activity_request(retoot_url)
        retoot_url = retoot.data.get("url", retoot.data["id"])

        original_tooter = ap_actor.Actor(retoot.data["attributedTo"])
        original_tooter.load()
        retooted_user = "@%s@%s" % (original_tooter.username, retoot_instance)
        retoot_content = _content(retoot.data)

        return (retoot.data.get("summary", None),  "%s (boost %s): %s" % (
            actor.username, retooted_user, retoot_content), retoot_url)

    elif type == "Create":
        content = _content(note)
        url = note.get("url", note["id"])

        return (note.get("summary", None),
            "%s: %s" % (actor.username, content), url)

    return None, None, None
