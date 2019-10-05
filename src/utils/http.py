import asyncio, ipaddress, re, signal, socket, traceback, typing
import urllib.error, urllib.parse, uuid
import json as _json
import bs4, netifaces, requests
import tornado.httpclient
from src import utils

REGEX_URL = re.compile("https?://\S+", re.I)

PAIRED_CHARACTERS = ["<>", "()"]

# best-effort tidying up of URLs
def url_sanitise(url: str):
    if not urllib.parse.urlparse(url).scheme:
        url = "http://%s" % url

    for pair_start, pair_end in PAIRED_CHARACTERS:
        # trim ")" from the end only if there's not a "(" to match it
        # google.com/) -> google.com/
        # google.com/() -> google.com/()
        # google.com/()) -> google.com/()
        if url.endswith(pair_end):
            if pair_start in url:
                open_index = url.rfind(pair_start)
                other_index = url.rfind(pair_end, 0, len(url)-1)
                if not other_index == -1 and other_index < open_index:
                    url = url[:-1]
            else:
                url = url[:-1]
    return url

DEFAULT_USERAGENT = ("Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/49.0.2623.87 Safari/537.36")

RESPONSE_MAX = (1024*1024)*100
SOUP_CONTENT_TYPES = ["text/html", "text/xml", "application/xml"]
DECODE_CONTENT_TYPES = ["text/plain"]+SOUP_CONTENT_TYPES
UTF8_CONTENT_TYPES = ["application/json"]

class HTTPException(Exception):
    pass
class HTTPTimeoutException(HTTPException):
    def __init__(self):
        Exception.__init__(self, "HTTP request timed out")
class HTTPParsingException(HTTPException):
    def __init__(self, message: str, data: str):
        Exception.__init__(self,
            "%s\n%s" % ((message or "HTTP parsing failed"), data))
class HTTPWrongContentTypeException(HTTPException):
    def __init__(self, message: str=None):
        Exception.__init__(self,
            message or "HTTP request gave wrong content type")

def throw_timeout():
    raise HTTPTimeoutException()

class Request(object):
    def __init__(self, url: str,
            get_params: typing.Dict[str, str]={}, post_data: typing.Any=None,
            headers: typing.Dict[str, str]={},

            json: bool=False, json_body: bool=False, allow_redirects: bool=True,
            check_content_type: bool=True, parse: bool=False,
            detect_encoding: bool=True,

            method: str="GET", parser: str="lxml", id: str=None,
            fallback_encoding: str=None, content_type: str=None,
            proxy: str=None, useragent: str=None,

            **kwargs):
        self.id = id or str(uuid.uuid4())

        self.set_url(url)
        self.method = method.upper()
        self.get_params = get_params
        self.post_data = post_data
        self.headers = headers

        self.json = json
        self.json_body = json_body
        self.allow_redirects = allow_redirects
        self.check_content_type = check_content_type
        self.parse = parse
        self.detect_encoding = detect_encoding

        self.parser = parser
        self.fallback_encoding = fallback_encoding
        self.content_type = content_type
        self.proxy = proxy
        self.useragent = useragent

        if kwargs:
            if method == "POST":
                self.post_data = kwargs
            else:
                self.get_params.update(kwargs)

    def set_url(self, url: str):
        if not urllib.parse.urlparse(url).scheme:
            url = "http://%s" % url
        self.url = url

    def get_headers(self) -> typing.Dict[str, str]:
        headers = self.headers.copy()
        if not "Accept-Language" in headers:
            headers["Accept-Language"] = "en-GB"
        if not "User-Agent" in headers:
            headers["User-Agent"] = self.useragent or DEFAULT_USERAGENT
        if not "Content-Type" in headers and self.content_type:
            headers["Content-Type"] = self.content_type
        return headers

    def get_body(self) -> typing.Any:
        if not self.post_data == None:
            if self.content_type == "application/json" or self.json_body:
                return _json.dumps(self.post_data)
            else:
                return self.post_data
        else:
            return None

class Response(object):
    def __init__(self, code: int, data: typing.Any,
            headers: typing.Dict[str, str], encoding: str):
        self.code = code
        self.data = data
        self.headers = headers
        self.content_type = headers.get("Content-Type", "").split(";", 1)[0]
        self.encoding = encoding

def _meta_content(s: str) -> typing.Dict[str, str]:
    out = {}
    for keyvalue in s.split(";"):
        key, _, value = keyvalue.strip().partition("=")
        out[key] = value
    return out

def _find_encoding(soup: bs4.BeautifulSoup) -> typing.Optional[str]:
    if not soup.meta == None:
        meta_charset = soup.meta.get("charset")
        if not meta_charset == None:
            return meta_charset

        meta_content_type = soup.findAll("meta",
            {"http-equiv": lambda v: (v or "").lower() == "content-type"})
        if meta_content_type:
            return _meta_content(meta_content_type[0].get("content"))["charset"]

    doctype = [item for item in soup.contents if isinstance(item,
        bs4.Doctype)] or None
    if doctype and doctype[0] == "html":
        return "utf8"

    return None

def request(request_obj: typing.Union[str, Request], **kwargs) -> Response:
    if type(request_obj) == str:
        request_obj = Request(request_obj, **kwargs)
    return _request(request_obj)

def _request(request_obj: Request) -> Response:

    def _wrap():
        headers = request_obj.get_headers()
        response = requests.request(
            request_obj.method,
            request_obj.url,
            headers=headers,
            params=request_obj.get_params,
            data=request_obj.get_body(),
            allow_redirects=request_obj.allow_redirects,
            stream=True
        )
        response_content = response.raw.read(RESPONSE_MAX,
            decode_content=True)
        if not response.raw.read(1) == b"":
            raise ValueError("Response too large")

        headers = utils.CaseInsensitiveDict(dict(response.headers))
        our_response = Response(response.status_code, response_content,
            headers=headers, encoding=response.encoding)
        return our_response

    try:
        response = utils.deadline_process(_wrap, seconds=5)
    except utils.DeadlineExceededException:
        raise HTTPTimeoutException()

    encoding = response.encoding or request_obj.fallback_encoding

    if not encoding:
        if response.content_type in UTF8_CONTENT_TYPES:
            encoding = "utf8"
        else:
            encoding = "iso-8859-1"

    if (request_obj.detect_encoding and
            response.content_type and
            response.content_type in SOUP_CONTENT_TYPES):
        souped = bs4.BeautifulSoup(response.data, request_obj.parser)
        encoding = _find_encoding(souped) or encoding

    def _decode_data():
        return response.data.decode(encoding)

    if request_obj.parse:
        if (not request_obj.check_content_type or
                response.content_type in SOUP_CONTENT_TYPES):
            souped = bs4.BeautifulSoup(_decode_data(), request_obj.parser)
            response.data = souped
            return response
        else:
            raise HTTPWrongContentTypeException(
                "Tried to soup non-html/non-xml data (%s)" %
                response.content_type)

    if request_obj.json and response.data:
        data = _decode_data()
        try:
            response.data = _json.loads(data)
            return response
        except _json.decoder.JSONDecodeError as e:
            raise HTTPParsingException(str(e), data)

    if response.content_type in DECODE_CONTENT_TYPES:
        response.data = _decode_data()
        return response
    else:
        return response

class RequestManyException(Exception):
    pass
def request_many(requests: typing.List[Request]) -> typing.Dict[str, Response]:
    responses = {}

    async def _request(request):
        client = tornado.httpclient.AsyncHTTPClient()
        url = request.url
        if request.get_params:
            url = "%s?%s" % (url, urllib.parse.urlencode(request.get_params))

        t_request = tornado.httpclient.HTTPRequest(
            request.url,
            connect_timeout=2, request_timeout=2,
            method=request.method,
            body=request.get_body(),
            headers=request.get_headers(),
            follow_redirects=request.allow_redirects,
        )

        try:
            response = await client.fetch(t_request)
        except:
            raise RequestManyException(
                "request_many failed for %s" % url)

        headers = utils.CaseInsensitiveDict(dict(response.headers))
        data = response.body.decode("utf8")
        responses[request.id] = Response(response.code, data, headers, "utf8")

    loop = asyncio.new_event_loop()
    awaits = []
    for request in requests:
        awaits.append(_request(request))
    task = asyncio.wait(awaits, loop=loop, timeout=5)
    loop.run_until_complete(task)
    loop.close()

    return responses

class Client(object):
    request = request
    request_many = request_many

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

def host_permitted(hostname: str) -> bool:
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
                return False
    for ip in ips:
        if ip.version == 6 and ip.ipv4_mapped:
            ip = ip.ipv4_mapped

        if (ip.is_loopback or
                ip.is_link_local or
                ip.is_multicast or
                ip.is_private):
            return False

    return True
