import json, re, traceback, urllib.request, urllib.parse, urllib.error
import bs4

USER_AGENT = ("Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/49.0.2623.87 Safari/537.36")
REGEX_HTTP = re.compile("https?://", re.I)

def remove_colon(s):
    if s.startswith(":"):
        s = s[1:]
    return s

def arbitrary(s, n):
    return remove_colon(" ".join(s[n:]))

def seperate_hostmask(hostmask):
    hostmask = remove_colon(hostmask)
    first_delim = hostmask.find("!")
    second_delim = hostmask.find("@")
    nickname = username = hostname = hostmask
    if first_delim > -1 and second_delim > first_delim:
        nickname, username = hostmask.split("!", 1)
        username, hostname = hostmask.split("@", 1)
    return nickname, username, hostname

def get_url(url, **kwargs):
    scheme = urllib.parse.urlparse(url).scheme
    if not scheme:
        url = "http://%s" % url

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
        response = urllib.request.urlopen(request)
    except urllib.error.HTTPError as e:
        traceback.print_exc()
        if kwargs.get("code"):
            return e.code, False
        else:
            return False

    response_content = response.read()
    encoding = response.info().get_content_charset()
    if kwargs.get("soup"):
        return bs4.BeautifulSoup(response_content, "lxml")
    if not encoding:
        soup = bs4.BeautifulSoup(response_content, "lxml")
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
        background = str(backbround).zfill(2)
    return "%s%s%s" % (FONT_COLOR, foreground,
        "" if not background else ",%s" % background)

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

IS_TRUE = ["true", "yes", "on", "y"]
IS_FALSE = ["false", "no", "off", "n"]
def bool_or_none(s):
    s = s.lower()
    if s in IS_TRUE:
        return True
    elif s in IS_FALSE:
        return False
