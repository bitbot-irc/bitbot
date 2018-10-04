import http.server, json, threading, urllib.parse
import flask

_bot = None
_events = None
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        _bot.lock.acquire()
        parsed = urllib.parse.urlparse(self.path)
        query = parsed.query
        get_params = urllib.parse.parse_qs(query)

        response = ""
        code = 404

        if parsed.path.startswith("/api/"):
            _, _, endpoint = parsed.path[1:].partition("/")
            response = _events.on("api").on(endpoint).call_for_result(
                params=get_params)

            if response:
                response = json.dumps(response, sort_keys=True, indent=4)
                code = 200

        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        try:
            self.wfile.write(response.encode("utf8"))
        except:
            pass
        _bot.lock.release()

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        global _bot
        _bot = bot

        self.events = events
        global _events
        _events = events

        if bot.get_setting("rest-api", False):
            self.httpd = http.server.HTTPServer(("", 5000), Handler)
            self.thread = threading.Thread(target=self.httpd.serve_forever)
            self.thread.daemon = True
            self.thread.start()

    def unload(self):
        self.httpd.shutdown()
