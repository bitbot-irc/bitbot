#--depends-on commands

import re, socket, typing
from src import ModuleManager, utils
import dns.resolver

URL_GEOIP = "http://ip-api.com/json/%s"
URL_IPINFO = "https://ipinfo.io/%s/json"
REGEX_IPv6 = r"(?:(?:[a-f0-9]{1,4}:){2,}|[a-f0-9:]*::)[a-f0-9:]*"
REGEX_IPv4 = r"(?:\d{1,3}\.){3}\d{1,3}"
REGEX_IP = re.compile("%s|%s" % (REGEX_IPv4, REGEX_IPv6), re.I)

def _parse(value):
    if utils.is_ip(value):
        return value
    return None

@utils.export("botset", utils.BoolSetting("configurable-nameservers",
    "Whether or not users can configure their own nameservers"))
@utils.export("serverset", utils.FunctionSetting(_parse, "dns-nameserver",
    "Set DNS nameserver", example="8.8.8.8"))
@utils.export("channelset", utils.FunctionSetting(_parse, "dns-nameserver",
    "Set DNS nameserver", example="8.8.8.8"))
class Module(ModuleManager.BaseModule):
    def _get_ip(self, event):
        ip = event["args_split"][0] if event["args"] else ""
        if not ip:
            line = event["target"].buffer.find(REGEX_IP)
            if line:
                ip = line.match
        if not ip:
            raise utils.EventError("No IP provided")
        return ip

    def _ipinfo_get(self, url):
        access_token = self.bot.config.get("ipinfo-token", None)
        headers = {}
        if not access_token == None:
            headers["Authorization"] = "Bearer %s" % access_token
        request = utils.http.Request(url, headers=headers)
        return utils.http.request(request)

    @utils.hook("received.command.dig", alias_of="dns")
    @utils.hook("received.command.dns", min_args=1)
    def dns(self, event):
        """
        :help: Get all addresses for a given hostname (IPv4/IPv6)
        :usage: <hostname> [type [type ...]]
        :prefix: DNS
        """
        args = event["args_split"][:]
        nameserver = None
        if self.bot.get_setting("configurable-nameservers", True):
            nameserver = event["target"].get_setting("dns-nameserver",
                event["server"].get_setting("dns-nameserver", None))
            for i, arg in enumerate(args):
                if arg[0] == "@":
                    nameserver = args.pop(i)[1:]
                    break

        hostname = args[0]

        record_types = args[1:]
        if not record_types:
            record_types = ["A?", "AAAA?"]

        if not nameserver == None:
            resolver = dns.resolver.Resolver(configure=False)
            resolver.nameservers = [nameserver]
        else:
            resolver = dns.resolver

        results = []

        for record_type in record_types:
            record_type_strip = record_type.rstrip("?").upper()
            try:
                query_result = resolver.resolve(hostname, record_type_strip,
                    lifetime=4)
                query_results = [q.to_text() for q in query_result]
                results.append([record_type_strip, query_result.rrset.ttl,
                    query_results])
            except dns.resolver.NXDOMAIN:
                raise utils.EventError("Domain not found")
            except dns.resolver.NoAnswer:
                if not record_type.endswith("?"):
                    raise utils.EventError("Domain does not have a '%s' record"
                        % record_type_strip)
            except dns.rdatatype.UnknownRdatatype:
               raise utils.EventError("Unknown record type '%s'"
                    % record_type_strip)
            except dns.exception.DNSException:
                message = "Failed to get DNS records"
                self.log.warn(message, exc_info=True)
                raise utils.EventError(message)

        results_str = ["%s (TTL %s): %s" %
            (t, ttl, ", ".join(r)) for t, ttl, r in results]
        event["stdout"].write("(%s) %s" % (hostname, " | ".join(results_str)))

    @utils.hook("received.command.geoip")
    def geoip(self, event):
        """
        :help: Get GeoIP data on a given IPv4/IPv6 address
        :usage: <IP>
        :prefix: GeoIP
        """
        ip = self._get_ip(event)

        page = utils.http.request(URL_GEOIP % ip).json()
        if page:
            if page["status"] == "success":
                hostname = None
                try:
                    hostname, alias, ips = socket.gethostbyaddr(page["query"])
                except (socket.herror, socket.gaierror):
                    pass

                data  = page["query"]
                data += " (%s)" % hostname if hostname else ""
                data += " | Organisation: %s" % page["org"]
                data += " | City: %s" % page["city"]
                data += " | Region: %s (%s)" % (
                    page["regionName"], page["countryCode"])
                data += " | ISP: %s (%s)" % (page["isp"], page["as"])
                data += " | Lon/Lat: %s/%s" % (page["lon"], page["lat"])
                data += " | Timezone: %s" % page["timezone"]
                event["stdout"].write(data)
            else:
                event["stderr"].write("No GeoIP data found")
        else:
            raise utils.EventResultsError()

    @utils.hook("received.command.ipinfo")
    def ipinfo(self, event):
        """
        :help: Get IPinfo.io data on a given IPv4/IPv6 address
        :usage: <IP>
        :prefix: IPinfo
        """
        ip = self._get_ip(event)

        page = self._ipinfo_get(URL_IPINFO % ip).json()
        if page:
            if page.get("error", False):
                if isinstance(page["error"], (list, dict)):
                    event["stderr"].write(page["error"]["message"])
                else:
                    event["stderr"].write(page["error"])
            elif page.get("ip", False):
                bogon = page.get("bogon", False)
                hostname = page.get("hostname", None)
                if not hostname and not bogon:
                    try:
                        hostname, alias, ips = socket.gethostbyaddr(page["ip"])
                    except (socket.herror, socket.gaierror):
                        pass

                data = page["ip"]
                if bogon:
                    data += " (Bogon)"
                else:
                    data += " (%s)" % hostname if hostname else ""
                    data += " (Anycast)" if page.get("anycast", False) == True else ""
                    if page.get("country", False):
                        data += " | City: %s" % page["city"]
                        data += " | Region: %s (%s)" % (page["region"], page["country"])
                        data += " | ISP: %s" % page.get("org", "Unknown")
                        data += " | Lon/Lat: %s" % page["loc"]
                        data += " | Timezone: %s" % page["timezone"]
                event["stdout"].write(data)
            else:
                event["stderr"].write("Unsupported endpoint")
        else:
            raise utils.EventResultsError()

    @utils.hook("received.command.rdns")
    def rdns(self, event):
        """
        :help: Do a reverse-DNS look up on an IPv4/IPv6 address
        :usage: <IP>
        :prefix: rDNS
        """
        ip = self._get_ip(event)

        try:
            hostname, alias, ips = socket.gethostbyaddr(ip)
        except (socket.herror, socket.gaierror) as e:
            raise utils.EventError(e.strerror)
        event["stdout"].write("(%s) %s" % (ips[0], hostname))
