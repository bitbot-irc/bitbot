#--depends-on commands
#--depends-on config
#--depends-on permissions

import binascii, http.server, json, os, socket, ssl, threading, urllib.parse
from bitbot import ModuleManager, utils

DEFAULT_PORT = 5001
DEFAULT_PUBLIC_PORT = 5000

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
        headers["Content-Length"] = len(self._data)
        return headers

    def get_data(self):
        return self._data

_module = None
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

    def _url_for(self, headers):
        return (lambda route, endpoint, args=[], get_params={}:
            _module._url_for(route, endpoint, args, get_params,
            headers.get("Host", None)))

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
                            args=args, data=data, headers=headers,
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
@utils.export("botset",
    utils.Setting("rest-api-host", "Public hostname:port for the REST API"))
class Module(ModuleManager.BaseModule):
    _name = "REST"

    def on_load(self):
        global _module
        _module = self

        global _bot
        _bot = self.bot

        global _events
        _events = self.events

        global _log
        _log = self.log

        self.exports.add("url-for", self._url_for)

        self.httpd = None
        if self.bot.get_setting("rest-api", False):
            self._start_httpd()

    def _start_httpd(self):
        port = int(self.bot.config.get("api-port", str(DEFAULT_PORT)))
        self.httpd = BitBotIPv6HTTPd(("::1", port), Handler)

        self.thread = threading.Thread(target=self.httpd.serve_forever)
        self.thread.daemon = True
        self.thread.start()
    def _stop_httpd(self):
        if self.httpd:
            self.httpd.shutdown()

    def on_resume(self):
        self._start_httpd()

    def unload(self):
        self._stop_httpd()
    def on_pause(self):
        self._stop_httpd()

    @utils.hook("received.command.apikey")
    @utils.kwarg("private_only", True)
    @utils.kwarg("min_args", 1)
    @utils.kwarg("usage", "list")
    @utils.kwarg("usage", "add <alias> [endpoint [endpoint ...]]")
    @utils.kwarg("usage", "remove <alias>")
    @utils.kwarg("usage", "info <alias>")
    @utils.kwarg("permission", "apikey")
    def apikey(self, event):
        subcommand = event["args_split"][0].lower()
        alias = None
        alias_lower = None
        found = None
        if len(event["args_split"]) > 1:
            alias = event["args_split"][1]
            alias_lower = alias.lower()

        api_keys = {}
        for key, value in self.bot.find_settings(prefix="api-key-"):
            api_keys[key] = value
            if alias and value["comment"].lower() == alias_lower:
                alias = value["comment"]
                found = key

        if subcommand == "list":
            aliases = [v["comment"] for v in api_keys.values()]
            aliases.sort()
            event["stdout"].write("API keys: %s" % ", ".join(aliases))
        elif subcommand == "add":
            if not len(event["args_split"]) > 1:
                raise utils.EventError(
                    "Please provide an alias for the API key")

            if found == None:
                comment = event["args_split"][1]
                new_key = binascii.hexlify(os.urandom(16)).decode("ascii")
                self.bot.set_setting("api-key-%s" % new_key, {
                    "comment": comment, "permissions": event["args_split"][2:]
                })
                event["stdout"].write("New API key '%s': %s" %
                    (comment, new_key))
            else:
                event["stderr"].write("API key alias '%s' already exists" %
                    alias)
        elif subcommand == "remove":
            if not len(event["args_split"]) > 1:
                raise utils.EventError("Please provide a key alias to remove")

            if not found == None:
                self.bot.del_setting(found)
                key = found.replace("api-key-", "", 1)
                event["stdout"].write("Deleted API key %s ('%s')" %
                    (key, alias))
            else:
                event["stderr"].write("Count not find API key '%s'" % alias)
        elif subcommand == "info":
            if not len(event["args_split"]) > 1:
                raise utils.EventError("Please provide a key alias to remove")

            if not found == None:
                key = found.replace("api-key-", "", 1)
                event["stdout"].write("API key %s ('%s') can access: %s" %
                    (key, alias, " ".join(api_keys[found]["permissions"])))
            else:
                event["stderr"].write("Count not find API key '%s'" % alias)

    def _url_for(self, route, endpoint, args=[], get_params={},
            host_override=None):
        host = host_override or self.bot.get_setting("rest-api-host", None)

        host, _, port = host.partition(":")
        if not port:
            port = str(_bot.config.get("api-port", DEFAULT_PUBLIC_PORT))
        host = "%s:%s" % (host, port)

        if host:
            args_str = ""
            if args:
                args_str = "/%s" % "/".join(args)
            get_params_str = ""
            if get_params:
                get_params_str = "?%s" % urllib.parse.urlencode(get_params)
            return "%s/%s/%s%s%s" % (host, route, endpoint, args_str,
                get_params_str)
        else:
            return None
