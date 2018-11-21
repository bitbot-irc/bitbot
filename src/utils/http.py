import re, signal, traceback, typing, urllib.error, urllib.parse
import json as _json
import bs4, requests

USER_AGENT = ("Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/49.0.2623.87 Safari/537.36")
REGEX_HTTP = re.compile("https?://", re.I)

RESPONSE_MAX = (1024*1024)*100

class HTTPException(Exception):
    pass
class HTTPTimeoutException(HTTPException):
    pass
class HTTPParsingException(HTTPException):
    pass

def throw_timeout():
    raise HTTPTimeoutException()

def get_url(url: str, method: str="GET", get_params: dict={},
        post_data: typing.Any=None, headers: dict={},
        json_data: typing.Any=None, code: bool=False, json: bool=False,
        soup: bool=False, parser: str="lxml", fallback_encoding: str="utf8"):

    if not urllib.parse.urlparse(url).scheme:
        url = "http://%s" % url

    if not "Accept-Language" in headers:
        headers["Accept-Language"] = "en-GB"
    if not "User-Agent" in headers:
        headers["User-Agent"] = USER_AGENT

    signal.signal(signal.SIGALRM, lambda _1, _2: throw_timeout())
    signal.alarm(5)
    try:
        response = requests.request(
            method.upper(),
            url,
            headers=headers,
            params=get_params,
            data=post_data,
            json=json_data,
            stream=True
        )
        response_content = response.raw.read(RESPONSE_MAX, decode_content=True)
    except TimeoutError:
        raise HTTPTimeoutException()
    finally:
        signal.signal(signal.SIGALRM, signal.SIG_IGN)

    if soup:
        soup = bs4.BeautifulSoup(response_content, parser)
        if code:
            return response.status_code, soup
        return soup

    data = response_content.decode(response.encoding or fallback_encoding)
    if json and data:
        try:
            data = _json.loads(data)
        except _json.decoder.JSONDecodeError as e:
            raise HTTPParsingException(str(e))

    if code:
        return response.status_code, data
    else:
        return data

def strip_html(s: str) -> str:
    return bs4.BeautifulSoup(s, "lxml").get_text()

