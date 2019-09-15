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

def activity_request(url, data=None, method="GET", type=ACTIVITY_TYPE):
    content_type = None
    headers = {}

    if method == "POST":
        content_type = type
    else:
        headers = {"Accept": type}

    request = utils.http.Request(url, headers=headers, useragent=USERAGENT,
        content_type=content_type, data=data, json=True, method=method)
    return utils.http.request(request).data

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
    for link in webfinger["links"]:
        if link["type"] == ACTIVITY_TYPE:
            return link["href"]

