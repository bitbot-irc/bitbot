import typing, urllib.parse
import socks
from src import ModuleManager, utils

TYPES = {
    "socks4": socks.SOCKS4,
    "socks5": socks.SOCKS5,
    "http": socks.HTTP
}

class ProxySetting(utils.Setting):
    def parse(self, value: str) -> typing.Any:
        parsed = urllib.parse.urlparse(value)
        if parsed.scheme in TYPES and parsed.hostname:
            return value

@utils.export("serverset", ProxySetting("proxy",
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
        return lambda host, port, bind, timeout: self._make_socket(
            ptype, phost, pport, host, port, bind, timeout)
    def _make_socket(self, ptype, phost, pport, host, port, bind, timeout):
        return socks.create_connection((host, port), 20, bind,
            ptype, phost, pport)
