import urllib.parse
import bs4
from src import IRCBot, utils

LD_TYPE = ("application/ld+json; "
    "profile=\"https://www.w3.org/ns/activitystreams\"")
JRD_TYPE = "application/jrd+json"
ACTIVITY_TYPE = "application/activity+json"
USERAGENT = "BitBot (%s) Fediverse" % IRCBot.VERSION

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

    request = utils.http.Request(url, headers=headers, useragent=USERAGENT,
        content_type=content_type, post_data=data, method=method, json=True,
        json_body=True)
    return utils.http.request(request)

HOSTMETA_TEMPLATE = "https://%s/.well-known/host-meta"
WEBFINGER_TEMPLATE = "https://%s/.well-known/webfinger?resource={uri}"

def find_actor(username, instance):
    hostmeta = HOSTMETA_TEMPLATE % instance
    hostmeta_request = utils.http.Request(HOSTMETA_TEMPLATE % instance,
        useragent=USERAGENT, parse=True, check_content_type=False)
    hostmeta = utils.http.request(hostmeta_request)

    webfinger_url = None
    for item in hostmeta.data.find_all("link"):
        if item["rel"] and item["rel"][0] == "lrdd":
            webfinger_url = item["template"]
            break

    if not webfinger_url:
        webfinger_url = WEBFINGER_TEMPLATE % instance
    webfinger_url = webfinger_url.replace("{uri}",
        "acct:%s@%s" % (username, instance), 1)

    webfinger = activity_request(webfinger_url, type=JRD_TYPE)

    actor_url = None
    for link in webfinger.data["links"]:
        if link["type"] == ACTIVITY_TYPE:
            return link["href"]

KNOWN_TAGS = ["p", "br"]

def _normalise_note(content):
    soup = bs4.BeautifulSoup(content, "html.parser")
    lines = []
    for element in soup.find_all():
        if element.text.strip() == "":
            element.decompose()
        elif not element.name in KNOWN_TAGS:
            element.unwrap()
    for element in soup.find_all():
        out = ""
        if element.name == "p":
            for subitem in element.contents:
                if type(subitem) == bs4.element.Tag:
                    if subitem.name == "br":
                        lines.append(out)
                        out = ""
                else:
                    out += subitem

        lines.append(out.replace("  ", " "))
    return "  ".join(lines)

def format_note(actor, note, type="Create"):
    if type == "Announce":
        retoot_url = note
        retoot_instance = urllib.parse.urlparse(retoot_url).hostname
        retoot = activity_request(retoot_url)
        retoot_url = retoot.data.get("url", retoot.data["id"])

        original_tooter = ap_actor.Actor(retoot.data["attributedTo"])
        original_tooter.load()
        retooted_user = "@%s@%s" % (original_tooter.username, retoot_instance)
        retoot_content = _normalise_note(retoot.data["content"])

        return (retoot.data.get("summary", None),  "%s (boost %s): %s - %s" % (
            actor.username, retooted_user, retoot_content), retoot_url)

    elif type == "Create":
        content = _normalise_note(note["content"])
        url = note.get("url", note["id"])

        return (note.get("summary", None),
            "%s: %s" % (actor.username, content), url)

    return None, None, None
