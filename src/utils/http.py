import asyncio, codecs, dataclasses, ipaddress, re, signal, socket, traceback
import typing, urllib.error, urllib.parse, uuid
import json as _json
import bs4, netifaces, requests, tornado.httpclient
from src import IRCBot, utils
from requests_toolbelt.adapters import source

REGEX_URL = re.compile("https?://\S+", re.I)

PAIRED_CHARACTERS = [("<", ">"), ("(", ")")]

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

USERAGENT = "Mozilla/5.0 (compatible; BitBot/%s; +%s)" % (
    IRCBot.VERSION, IRCBot.URL)

RESPONSE_MAX = (1024*1024)*100
SOUP_CONTENT_TYPES = ["text/html", "text/xml", "application/xml"]
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

@dataclasses.dataclass
class Request(object):
    url: str
    id: typing.Optional[str] = None
    method: str = "GET"

    get_params: typing.Dict[str, str] = dataclasses.field(
        default_factory=dict)
    post_data: typing.Any = None
    headers: typing.Dict[str, str] = dataclasses.field(
        default_factory=dict)
    cookies: typing.Dict[str, str] = dataclasses.field(
        default_factory=dict)

    json_body: bool = False

    allow_redirects: bool = True
    check_hostname: bool = False
    check_content_type: bool = True
    fallback_encoding: typing.Optional[str] = None
    content_type: typing.Optional[str] = None
    proxy: typing.Optional[str] = None
    useragent: typing.Optional[str] = None

    timeout: int=5

    bindhost: typing.Optional[str] = None

    def validate(self):
        self.id = self.id or str(uuid.uuid4())
        self.set_url(self.url)
        self.method = self.method.upper()

    def set_url(self, url: str):
        parts = urllib.parse.urlparse(url)
        if not parts.scheme:
            parts = urllib.parse.urlparse("http://%s" % url)

        netloc = codecs.encode(parts.netloc, "idna").decode("ascii")
        params = "" if not parts.params else (";%s" % parts.params)
        query = "" if not parts.query else ("?%s" % parts.query)
        fragment = "" if not parts.fragment else ("#%s" % parts.fragment)

        self.url = (
            f"{parts.scheme}://{netloc}{parts.path}{params}{query}{fragment}")

    def get_headers(self) -> typing.Dict[str, str]:
        headers = self.headers.copy()
        if not "Accept-Language" in headers:
            headers["Accept-Language"] = "en-GB,en;q=0.5"
        if not "User-Agent" in headers:
            headers["User-Agent"] = self.useragent or USERAGENT
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
    def __init__(self, code: int, data: bytes, encoding: str,
            headers: typing.Dict[str, str], cookies: typing.Dict[str, str]):
        self.code = code
        self.data = data
        self.content_type = headers.get("Content-Type", "").split(";", 1)[0]
        self.encoding = encoding
        self.headers = headers
        self.cookies = cookies
    def decode(self, encoding: typing.Optional[str]=None) -> str:
        return self.data.decode(encoding or self.encoding)
    def json(self) -> typing.Any:
        return _json.loads(self.data)
    def soup(self, parser: str="html5lib") -> bs4.BeautifulSoup:
        return bs4.BeautifulSoup(self.decode(), parser)

def _split_content(s: str) -> typing.Dict[str, str]:
    out = {}
    for keyvalue in s.split(";"):
        key, _, value = keyvalue.strip().partition("=")
        out[key] = value
    return out

def _find_encoding(headers: typing.Dict[str, str], data: bytes
        ) -> typing.Optional[str]:
    if "Content-Type" in headers:
        content_header = _split_content(headers["Content-Type"])
        if "charset" in content_header:
            return content_header["charset"]

    soup = bs4.BeautifulSoup(data, "html5lib")
    if not soup.meta == None:
        meta_charset = soup.meta.get("charset")
        if not meta_charset == None:
            return meta_charset

        meta_content_type = soup.findAll("meta",
            {"http-equiv": lambda v: (v or "").lower() == "content-type"})
        if meta_content_type:
            meta_content = _split_content(meta_content_type[0].get("content"))
            if "charset" in meta_content:
                return meta_content["charset"]

    doctype = [item for item in soup.contents if isinstance(item,
        bs4.Doctype)] or None
    if doctype and doctype[0] == "html":
        return "utf8"

    return None

def request(request_obj: typing.Union[str, Request], **kwargs) -> Response:
    if isinstance(request_obj, str):
        request_obj = Request(request_obj, **kwargs)
    return _request(request_obj)

class HostNameInvalidError(ValueError):
    pass
class TooManyRedirectionsError(Exception):
    pass

def _request(request_obj: Request) -> Response:
    request_obj.validate()

    def _assert_allowed(url: str):
        hostname = urllib.parse.urlparse(url).hostname
        if hostname is None or not host_permitted(hostname):
            raise HostNameInvalidError(
                f"hostname {hostname} is not permitted")

    def _wrap() -> Response:
        headers = request_obj.get_headers()

        redirect = 0
        current_url = request_obj.url
        session = requests.Session()
        if not request_obj.bindhost is None:
            new_source = source.SourceAddressAdapter(request_obj.bindhost)
            session.mount('http://', new_source)
            session.mount('https://', new_source)

        while True:
            if request_obj.check_hostname:
                _assert_allowed(current_url)

            response = session.request(
                request_obj.method,
                current_url,
                headers=headers,
                params=request_obj.get_params,
                data=request_obj.get_body(),
                allow_redirects=False,
                stream=True,
                cookies=request_obj.cookies
            )

            if response.status_code in [301, 302]:
                redirect += 1
                if redirect == 5:
                    raise TooManyRedirectionsError(f"{redirect} redirects")
                else:
                    current_url = response.headers["location"]
                    continue

            response_content = response.raw.read(RESPONSE_MAX,
                decode_content=True)
            if not response.raw.read(1) == b"":
                raise ValueError("Response too large")
            break

        session.close()

        headers = utils.CaseInsensitiveDict(dict(response.headers))
        our_response = Response(response.status_code, response_content,
            encoding=response.encoding, headers=headers,
            cookies=response.cookies.get_dict())
        return our_response

    try:
        response = utils.deadline_process(_wrap, seconds=request_obj.timeout)
    except utils.DeadlineExceededException:
        raise HTTPTimeoutException()

    encoding = response.encoding or request_obj.fallback_encoding

    if not encoding:
        if response.content_type in UTF8_CONTENT_TYPES:
            encoding = "utf8"
        else:
            encoding = "iso-8859-1"

    if (response.content_type and
            response.content_type in SOUP_CONTENT_TYPES):
        encoding = _find_encoding(response.headers, response.data) or encoding
    response.encoding = encoding

    return response

class Session(object):
    def __init__(self):
        self._cookies: typing.Dict[str, str] = {}
    def __enter__(self):
        pass
    def __exit__(self):
        self._cookies.clear()

    def request(self, request: Request) -> Response:
        request.cookies.update(self._cookies)
        response = _request(request)
        self._cookies.update(response.cookies)
        return response

class RequestManyException(Exception):
    pass
def request_many(requests: typing.List[Request]) -> typing.Dict[str, Response]:
    responses = {}

    async def _request(request):
        request.validate()
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
        encoding = _find_encoding(headers, response.body) or "utf8"
        responses[request.id] = Response(response.code, response.body, encoding,
            headers, {})

    loop = asyncio.new_event_loop()
    awaits = []
    for request in requests:
        awaits.append(_request(request))
    task = asyncio.wait(awaits, timeout=5)
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
