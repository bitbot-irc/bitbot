import asyncio, ipaddress, re, signal, socket, traceback, typing
import urllib.error, urllib.parse
import json as _json
import bs4, netifaces, requests
import tornado.httpclient
from src import utils

REGEX_URL = re.compile("https?://[A-Z0-9{}]+".format(re.escape("-._~:/%?#[]@!$&'()*+,;=")), re.I)

# best-effort tidying up of URLs
def url_sanitise(url: str):
    if not urllib.parse.urlparse(url).scheme:
        url = "http://%s" % url

    if url.endswith(")"):
        # trim ")" from the end only if there's not a "(" to match it
        # google.com/) -> google.com/
        # google.com/() -> google.com/()
        # google.com/()) -> google.com/()

        if "(" in url:
            open_index = url.rfind("(")
            other_index = url.rfind(")", 0, len(url)-1)
            if other_index == -1 or other_index < open_index:
                return url
        return url[:-1]
    return url

USER_AGENT = ("Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/49.0.2623.87 Safari/537.36")

RESPONSE_MAX = (1024*1024)*100
SOUP_CONTENT_TYPES = ["text/html", "text/xml", "application/xml"]

class HTTPException(Exception):
    pass
class HTTPTimeoutException(HTTPException):
    def __init__(self):
        Exception.__init__(self, "HTTP request timed out")
class HTTPParsingException(HTTPException):
    def __init__(self, message: str=None):
        Exception.__init__(self, message or "HTTP parsing failed")
class HTTPWrongContentTypeException(HTTPException):
    def __init__(self, message: str=None):
        Exception.__init__(self,
            message or "HTTP request gave wrong content type")

def throw_timeout():
    raise HTTPTimeoutException()

class Response(object):
    def __init__(self, code: int, data: typing.Any,
            headers: typing.Dict[str, str]):
        self.code = code
        self.data = data
        self.headers = headers

def request(url: str, method: str="GET", get_params: dict={},
        post_data: typing.Any=None, headers: dict={},
        json_data: typing.Any=None, code: bool=False, json: bool=False,
        soup: bool=False, parser: str="lxml", fallback_encoding: str="utf8",
        allow_redirects: bool=True, check_content_type: bool=True
        ) -> Response:

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
            allow_redirects=allow_redirects,
            stream=True
        )
        response_content = response.raw.read(RESPONSE_MAX, decode_content=True)
    except TimeoutError:
        raise HTTPTimeoutException()
    finally:
        signal.signal(signal.SIGALRM, signal.SIG_IGN)

    response_headers = utils.CaseInsensitiveDict(dict(response.headers))
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0]

    def _decode_data():
        return response_content.decode(response.encoding or fallback_encoding)

    if soup:
        if not check_content_type or content_type in SOUP_CONTENT_TYPES:
            soup = bs4.BeautifulSoup(_decode_data(), parser)
            return Response(response.status_code, soup, response_headers)
        else:
            raise HTTPWrongContentTypeException(
                "Tried to soup non-html/non-xml data (%s)" % content_type)

    data = _decode_data()
    if json and data:
        try:
            return Response(response.status_code, _json.loads(data),
                response_headers)
        except _json.decoder.JSONDecodeError as e:
            raise HTTPParsingException(str(e))

    return Response(response.status_code, data, response_headers)

def request_many(urls: typing.List[str]) -> typing.Dict[str, Response]:
    responses = {}

    async def _request(url):
        client = tornado.httpclient.AsyncHTTPClient()
        request = tornado.httpclient.HTTPRequest(url, method="GET",
            connect_timeout=2, request_timeout=2)

        response = await client.fetch(request)

        headers = utils.CaseInsensitiveDict(dict(response.headers))
        data = response.body.decode("utf8")
        responses[url] = Response(response.code, data, headers)

    loop = asyncio.new_event_loop()
    awaits = []
    for url in urls:
        awaits.append(_request(url))
    task = asyncio.wait(awaits, loop=loop, timeout=5)
    loop.run_until_complete(task)
    loop.close()

    return responses

def strip_html(s: str) -> str:
    return bs4.BeautifulSoup(s, "lxml").get_text()

def resolve_hostname(hostname: str) -> typing.List[str]:
    try:
        addresses = socket.getaddrinfo(hostname, None, 0, socket.SOCK_STREAM)
    except:
        return []
    return [address[-1][0] for address in addresses]

def is_ip(addr: str) -> bool:
    try:
        ipaddress.ip_address(addr)
    except ValueError:
        return False
    return True

def is_localhost(hostname: str) -> bool:
    if is_ip(hostname):
        ips = [ipaddress.ip_address(hostname)]
    else:
        ips = [ipaddress.ip_address(ip) for ip in resolve_hostname(hostname)]

    for interface in netifaces.interfaces():
        links = netifaces.ifaddresses(interface)

        for link in links.get(netifaces.AF_INET, []
                )+links.get(netifaces.AF_INET6, []):
            address = ipaddress.ip_address(link["addr"].split("%", 1)[0])
            if address in ips:
                return True

    return False
