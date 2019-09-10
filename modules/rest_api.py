#--depends-on commands
#--depends-on config
#--depends-on permissions
#--require-config tls-api-key
#--require-config tls-api-certificate

import http.server, json, socket, ssl, threading, uuid, urllib.parse
from src import ModuleManager, utils

class Response(object):
    def __init__(self, compact=False):
        self._compact = compact
        self._headers = {}
        self._data = b""
        self.code = 200
        self.content_type = "text/plain"
    def write(self, data):
        self._data += data
    def write_text(self, data):
        self._data += data.encode("utf8")
    def write_json(self, obj):
        if self._compact:
            data = json.dumps(obj, separators=(",", ":"))
        else:
            data = json.dumps(obj, sort_keys=True, indent=4)
        self._data += data.encode("utf8")

    def set_header(self, key: str, value: str):
        self._headers[key] = value
    def get_headers(self):
        headers = {}
        has_content_type = False
        for key, value in self._headers.items():
            if key.lower() == "content-type":
                has_content_type = True
            headers[key] = value
        if not has_content_type:
            headers["Content-Type"] = self.content_type
        return headers

    def get_data(self):
        return self._data

_bot = None
_events = None
_log = None
class Handler(http.server.BaseHTTPRequestHandler):
    timeout = 10

    def _path_data(self):
        path = urllib.parse.urlparse(self.path).path
        _, _, endpoint = path[1:].partition("/")
        endpoint, _, args = endpoint.partition("/")
        args = list(filter(None, args.split("/")))
        return path, endpoint, args

    def _url_params(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        return dict([(k, v[0]) for k, v in query.items()])

    def _body(self):
        content_length = int(self.headers.get("content-length", 0))
        return self.rfile.read(content_length)

    def _respond(self, response):
        self.send_response(response.code)
        for key, value in response.get_headers().items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response.get_data())

    def _key_settings(self, key):
        return _bot.get_setting("api-key-%s" % key, {})
    def _minify_setting(self):
        return _bot.get_setting("rest-api-minify", False)

    def url_for(self, headers, route, endpoint, get_params={}):
        hostname = headers.get("Host", None)
        if not hostname:
            return None
        else:
            get_params_str = ""
            if get_params:
                get_params = "?%s" % urllib.parse.urlencode(get_params)
            return "%s/%s/%s%s" % (hostname, route, endpoint, get_params_str)
    def _url_for(self, headers):
        return lambda route, endpoint, get_params={}: self.url_for(
            headers, route, endpoint, get_params)

    def _handle(self, method, path, endpoint, args):
        headers = utils.CaseInsensitiveDict(dict(self.headers.items()))
        params = self._url_params()
        data = self._body()

        response = Response(compact=self._minify_setting())
        response.code = 404

        hooks = _events.on("api").on(method).on(endpoint).get_hooks()
        if hooks:
            response.code = 200
            hook = hooks[0]
            authenticated = hook.get_kwarg("authenticated", True)
            key = params.get("key", None)
            key_setting = self._key_settings(key)
            permissions = key_setting.get("permissions", [])

            if key_setting:
                _log.debug("[HTTP] %s from API key %s (%s)",
                    [method, key, key_setting["comment"]])

            if not authenticated or path in permissions or "*" in permissions:
                if path.startswith("/api/"):
                    event_response = None
                    try:
                        event_response = _events.on("api").on(method).on(
                            endpoint).call_for_result_unsafe(params=params,
                            path=args, data=data, headers=headers,
                            response=response, url_for=self._url_for(headers))
                    except Exception as e:
                        _log.error("failed to call API endpoint \"%s\"",
                            [path], exc_info=True)
                        response.code = 500

                    if not event_response == None:
                        response.write_json(event_response)
                        response.content_type = "application/json"
            else:
                response.code = 401
        return response

    def _handle_wrap(self, method):
        path, endpoint, args = self._path_data()
        _log.debug("[HTTP] starting _handle for %s from %s:%d: %s",
            [method, self.client_address[0], self.client_address[1], path])

        response = _bot.trigger(lambda: self._handle(method, path, endpoint,
            args))
        self._respond(response)

        _log.debug("[HTTP] finishing _handle for %s from %s:%d (%d)",
            [method, self.client_address[0], self.client_address[1],
            response.code])

    def do_GET(self):
        self._handle_wrap("GET")

    def do_POST(self):
        self._handle_wrap("POST")

    def log_message(self, format, *args):
        return

class BitBotIPv6HTTPd(http.server.HTTPServer):
    address_family = socket.AF_INET6

@utils.export("botset",
    utils.BoolSetting("rest-api", "Enable/disable REST API"))
@utils.export("botset",
    utils.BoolSetting("rest-api-minify", "Enable/disable REST API minifying"))
class Module(ModuleManager.BaseModule):
    def on_load(self):
        global _bot
        _bot = self.bot

        global _events
        _events = self.events

        global _log
        _log = self.log

        self.httpd = None
        if self.bot.get_setting("rest-api", False):
            port = int(self.bot.config.get("api-port", "5000"))
            self.httpd = BitBotIPv6HTTPd(("", port), Handler)

            self.httpd.socket = utils.security.ssl_wrap(self.httpd.socket,
                cert=self.bot.config["tls-api-certificate"],
                key=self.bot.config["tls-api-key"],
                server_side=True, verify=False)

            self.thread = threading.Thread(target=self.httpd.serve_forever)
            self.thread.daemon = True
            self.thread.start()

    def unload(self):
        if self.httpd:
            self.httpd.shutdown()

    @utils.hook("received.command.apikey", private_only=True, min_args=1)
    def api_key(self, event):
        """
        :help: Generate a new API key
        :usage: <comment> [endpoint [endpoint ...]]
        :permission: api-key
        :prefix: APIKey
        """
        api_key = uuid.uuid4().hex
        comment = event["args_split"][0]
        self.bot.set_setting("api-key-%s" % api_key, {
            "comment": comment,
            "permissions": event["args_split"][1:]
        })
        event["stdout"].write("New API key ('%s'): %s" % (comment, api_key))
