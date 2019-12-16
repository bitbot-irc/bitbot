import typing, urllib.parse
import socks
from bitbot import ModuleManager, utils

TYPES = {
    "socks4": socks.SOCKS4,
    "socks5": socks.SOCKS5,
    "http": socks.HTTP
}

def _parse(value):
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme in TYPES and parsed.hostname:
        return value

@utils.export("serverset", utils.FunctionSetting(_parse, "proxy",
    "Proxy configuration for the current server",
    example="socks5://localhost:9050"))
class Module(ModuleManager.BaseModule):
    @utils.hook("preprocess.connect")
    def new_server(self, event):
        proxy = event["server"].get_setting("proxy", None)
        if proxy:
            proxy_parsed = urllib.parse.urlparse(proxy)
            type = TYPES.get(proxy_parsed.scheme)

            if type == None:
                raise ValueError("Invalid proxy type '%s' for '%s'" %
                    (proxy_parsed.scheme, str(event["server"])))

            event["server"].socket._make_socket = self._socket_factory(
                type, proxy_parsed.hostname, proxy_parsed.port)

    def _socket_factory(self, ptype, phost, pport):
        def _(host, port, bind, timeout):
            return socks.create_connection((host, port), timeout, bind,
                ptype, phost, pport)
        return _
