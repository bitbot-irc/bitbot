import json, re, traceback, urllib.request, urllib.parse, urllib.error, ssl
import string
import bs4

USER_AGENT = ("Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/49.0.2623.87 Safari/537.36")
REGEX_HTTP = re.compile("https?://", re.I)

RFC1459_UPPER = r'\[]~'
RFC1459_UPPER = r'|{}^'

def remove_colon(s):
    if s.startswith(":"):
        s = s[1:]
    return s

def arbitrary(s, n):
    return remove_colon(" ".join(s[n:]))

def _rfc1459_lower(s):
    for upper, lower in zip(RFC1459_UPPER, RFC1459_LOWER):
        s = s.replace(upper, lower)
    return s.lower()
def irc_lower(server, s):
    if server.case_mapping == "ascii":
        return s.lower()
    elif server.case_mapping == "rfc1459":
        return _rfc1459_lower(s)
    else:
        raise ValueError("unknown casemapping '%s'" % server.case_mapping)

def irc_equals(server, s1, s2):
    return irc_lower(server, s1) == irc_lower(server, s2)

class IRCHostmask(object):
    def __init__(self, nickname, username, hostname, hostmask):
        self.nickname = nickname
        self.username = username
        self.hostname = hostname
        self.hostmask = hostmask
def seperate_hostmask(hostmask):
    hostmask = remove_colon(hostmask)
    first_delim = hostmask.find("!")
    second_delim = hostmask.find("@")
    nickname = username = hostname = hostmask
    if first_delim > -1 and second_delim > first_delim:
        nickname, username = hostmask.split("!", 1)
        username, hostname = username.split("@", 1)
    return IRCHostmask(nickname, username, hostname, hostmask)

def get_url(url, **kwargs):
    if not urllib.parse.urlparse(url).scheme:
        url = "http://%s" % url
    url_parsed = urllib.parse.urlparse(url)

    method = kwargs.get("method", "GET")
    get_params = kwargs.get("get_params", "")
    post_params = kwargs.get("post_params", None)
    headers = kwargs.get("headers", {})
    if get_params:
        get_params = "?%s" % urllib.parse.urlencode(get_params)
    if post_params:
        post_params = urllib.parse.urlencode(post_params).encode("utf8")
    url = "%s%s" % (url, get_params)
    try:
        url.encode("latin-1")
    except UnicodeEncodeError:
        if kwargs.get("code"):
            return 0, False
        return False

    request = urllib.request.Request(url, post_params)
    request.add_header("Accept-Language", "en-US")
    request.add_header("User-Agent", USER_AGENT)
    for header, value in headers.items():
        request.add_header(header, value)
    request.method = method

    try:
        response = urllib.request.urlopen(request, timeout=5)
    except urllib.error.HTTPError as e:
        traceback.print_exc()
        if kwargs.get("code"):
            return e.code, False
        return False
    except urllib.error.URLError as e:
        traceback.print_exc()
        if kwargs.get("code"):
            return -1, False
        return False
    except ssl.CertificateError as e:
        traceback.print_exc()
        if kwargs.get("code"):
            return -1, False,
        return False

    response_content = response.read()
    encoding = response.info().get_content_charset()
    if kwargs.get("soup"):
        return bs4.BeautifulSoup(response_content, kwargs.get("parser", "lxml"))
    if not encoding:
        soup = bs4.BeautifulSoup(response_content, kwargs.get("parser", "lxml"))
        metas = soup.find_all("meta")
        for meta in metas:
            if "charset=" in meta.get("content", ""):
                encoding = meta.get("content").split("charset=", 1)[1
                    ].split(";", 1)[0]
            elif meta.get("charset", ""):
                encoding = meta.get("charset")
            else:
                continue
            break
        if not encoding:
            for item in soup.contents:
                if isinstance(item, bs4.Doctype):
                    if item == "html":
                        encoding = "utf8"
                    else:
                        encoding = "latin-1"
                    break
    response_content = response_content.decode(encoding or "utf8")
    data = response_content
    if kwargs.get("json") and data:
        try:
            data = json.loads(response_content)
        except json.decoder.JSONDecodeError:
            traceback.print_exc()
            return False
    if kwargs.get("code"):
        return response.code, data
    else:
        return data

COLOR_WHITE, COLOR_BLACK, COLOR_BLUE, COLOR_GREEN = 0, 1, 2, 3
COLOR_RED, COLOR_BROWN, COLOR_PURPLE, COLOR_ORANGE = 4, 5, 6, 7
COLOR_YELLOW, COLOR_LIGHTGREEN, COLOR_CYAN, COLOR_LIGHTCYAN = (8, 9,
    10, 11)
COLOR_LIGHTBLUE, COLOR_PINK, COLOR_GREY, COLOR_LIGHTGREY = (12, 13,
    14, 15)
FONT_BOLD, FONT_ITALIC, FONT_UNDERLINE, FONT_INVERT = ("\x02", "\x1D",
    "\x1F", "\x16")
FONT_COLOR, FONT_RESET = "\x03", "\x0F"

def color(foreground, background=None):
    foreground = str(foreground).zfill(2)
    if background:
        background = str(background).zfill(2)
    return "%s%s%s" % (FONT_COLOR, foreground,
        "" if not background else ",%s" % background)

def bold(s):
    return "%s%s%s" % (FONT_BOLD, s, FONT_BOLD)

def underline(s):
    return "%s%s%s" % (FONT_UNDERLINE, s, FONT_UNDERLINE)

TIME_SECOND = 1
TIME_MINUTE = TIME_SECOND*60
TIME_HOUR = TIME_MINUTE*60
TIME_DAY = TIME_HOUR*24
TIME_WEEK = TIME_DAY*7

def time_unit(seconds):
    since = None
    unit = None
    if seconds >= TIME_WEEK:
        since = seconds/TIME_WEEK
        unit = "week"
    elif seconds >= TIME_DAY:
        since = seconds/TIME_DAY
        unit = "day"
    elif seconds >= TIME_HOUR:
        since = seconds/TIME_HOUR
        unit = "hour"
    elif seconds >= TIME_MINUTE:
        since = seconds/TIME_MINUTE
        unit = "minute"
    else:
        since = seconds
        unit = "second"
    since = int(since)
    if since > 1:
        unit = "%ss" % unit # pluralise the unit
    return [since, unit]

REGEX_PRETTYTIME = re.compile("\d+[wdhms]", re.I)

SECONDS_MINUTES = 60
SECONDS_HOURS = SECONDS_MINUTES*60
SECONDS_DAYS = SECONDS_HOURS*24
SECONDS_WEEKS = SECONDS_DAYS*7

def from_pretty_time(pretty_time):
    seconds = 0
    for match in re.findall(REGEX_PRETTYTIME, pretty_time):
        number, unit = int(match[:-1]), match[-1].lower()
        if unit == "m":
            number = number*SECONDS_MINUTES
        elif unit == "h":
            number = number*SECONDS_HOURS
        elif unit == "d":
            number = number*SECONDS_DAYS
        elif unit == "w":
            number = number*SECONDS_WEEKS
        seconds += number
    if seconds > 0:
        return seconds

UNIT_SECOND = 5
UNIT_MINUTE = 4
UNIT_HOUR = 3
UNIT_DAY = 2
UNIT_WEEK = 1
def to_pretty_time(total_seconds, minimum_unit=UNIT_SECOND, max_units=6):
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)
    out = ""

    units = 0
    if weeks and minimum_unit >= UNIT_WEEK and units < max_units:
        out += "%dw" % weeks
        units += 1
    if days and minimum_unit >= UNIT_DAY and units < max_units:
        out += "%dd" % days
        units += 1
    if hours and minimum_unit >= UNIT_HOUR and units < max_units:
        out += "%dh" % hours
        units += 1
    if minutes and minimum_unit >= UNIT_MINUTE and units < max_units:
        out += "%dm" % minutes
        units += 1
    if seconds and minimum_unit >= UNIT_SECOND and units < max_units:
        out += "%ds" % seconds
        units += 1
    return out

IS_TRUE = ["true", "yes", "on", "y"]
IS_FALSE = ["false", "no", "off", "n"]
def bool_or_none(s):
    s = s.lower()
    if s in IS_TRUE:
        return True
    elif s in IS_FALSE:
        return False
def int_or_none(s):
    stripped_s = s.lstrip("0")
    if stripped_s.isdigit():
        return int(stripped_s)

def get_closest_setting(event, setting, default=None):
    server = event["server"]
    if "channel" in event:
        closest = event["channel"]
    elif "target" in event and "is_channel" in event and event["is_channel"]:
        closest = event["target"]
    else:
        closest = event["user"]
    return closest.get_setting(setting, server.get_setting(setting, default))

def prevent_highlight(nickname):
    return nickname[0]+"\u200d"+nickname[1:]
