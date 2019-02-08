#--require-config tls-api-key
#--require-config tls-api-certificate

import http.server, json, ssl, threading, uuid, urllib.parse
from src import ModuleManager, utils

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

    def _respond(self, code, headers, data):
        self.send_response(code)
        for key, value in headers:
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data.encode("utf8"))

    def _handle(self, method):
        path, endpoint, args = self._path_data()
        headers = utils.CaseInsensitiveDict(dict(self.headers.items()))
        params = self._url_params()
        data = self._body()

        response = ""
        code = 404
        content_type = "text/plain"

        hooks = _events.on("api").on(method).on(endpoint).get_hooks()
        if hooks:
            hook = hooks[0]
            authenticated = hook.get_kwarg("authenticated", True)
            key = params.get("key", None)
            key_setting = _bot.get_setting("api-key-%s" % key, {})
            permissions = key_setting.get("permissions", [])

            if key_setting:
                _log.debug("[HTTP] %s from API key %s (%s)",
                    [method, key, key_setting["comment"]])

            if not authenticated or path in permissions or "*" in permissions:
                if path.startswith("/api/"):
                    event_response = None
                    try:
                        event_response = _bot.trigger(lambda:
                            _events.on("api").on(method).on(
                            endpoint).call_unsafe_for_result(params=params,
                            path=args, data=data, headers=headers))
                    except Exception as e:
                        _log.error("failed to call API endpoint \"%s\"",
                            [path], exc_info=True)
                        code = 500

                    if not event_response == None:
                        content_type = "application/json"
                        if _bot.get_setting("rest-api-minify", False):
                            response = json.dumps(event_response,
                                sort_keys=True, separators=(",", ":"))
                        else:
                            response = json.dumps(event_response,
                                sort_keys=True, indent=4)
                        code = 200
            else:
                code = 401

        headers = {
            "Content-type": content_type
        }

        self._respond(code, headers, response)


    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def log_message(self, format, *args):
        _log.info("[HTTP] " + format, args)

@utils.export("botset", {"setting": "rest-api",
    "help": "Enable/disable REST API",
    "validate": utils.bool_or_none})
@utils.export("botset", {"setting": "rest-api-minify",
    "help": "Enable/disable REST API minifying",
    "validate": utils.bool_or_none})
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
            self.httpd = http.server.HTTPServer(("", 5000), Handler)
            self.httpd.socket = ssl.wrap_socket(self.httpd.socket,
                keyfile=self.bot.config["tls-api-key"],
                certfile=self.bot.config["tls-api-certificate"],
                server_side=True)
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
