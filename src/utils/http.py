import re, traceback, urllib.error, urllib.parse, urllib.request
import json, ssl
import bs4

USER_AGENT = ("Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/49.0.2623.87 Safari/537.36")
REGEX_HTTP = re.compile("https?://", re.I)

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

def strip_html(s):
    return bs4.BeautifulSoup(s, "lxml").get_text()

