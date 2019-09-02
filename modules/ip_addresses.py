#--depends-on commands

import re, socket, typing
from src import ModuleManager, utils
import dns.resolver

URL_GEOIP = "http://ip-api.com/json/%s"
REGEX_IPv6 = r"(?:(?:[a-f0-9]{1,4}:){2,}|[a-f0-9:]*::)[a-f0-9:]*"
REGEX_IPv4 = r"(?:\d{1,3}\.){3}\d{1,3}"
REGEX_IP = re.compile("%s|%s" % (REGEX_IPv4, REGEX_IPv6), re.I)

class DnsSetting(utils.Setting):
    def parse(self, value: str) -> typing.Any:
        if utils.is_ip(value):
            return value
        return None

@utils.export("botset", utils.BoolSetting("configurable-nameservers",
    "Whether or not users can configure their own nameservers"))
@utils.export("serverset", DnsSetting("dns-nameserver",
    "Set DNS nameserver", example="8.8.8.8"))
@utils.export("channelset", DnsSetting("dns-nameserver",
    "Set DNS nameserver", example="8.8.8.8"))
class Module(ModuleManager.BaseModule):
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
            nameserver = event["channel"].get_setting("dns-nameserver",
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
                query_result = resolver.query(hostname, record_type_strip,
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

    @utils.hook("received.command.geoip", min_args=1)
    def geoip(self, event):
        """
        :help: Get geoip data on a given IPv4/IPv6 address
        :usage: <IP>
        :prefix: GeoIP
        """
        page = utils.http.request(URL_GEOIP % event["args_split"][0],
            json=True)
        if page:
            if page.data["status"] == "success":
                data  = page.data["query"]
                data += " | Organisation: %s" % page.data["org"]
                data += " | City: %s" % page.data["city"]
                data += " | Region: %s (%s)" % (page.data["regionName"],
                    page.data["countryCode"])
                data += " | ISP: %s" % page.data["isp"]
                data += " | Lon/Lat: %s/%s" % (page.data["lon"],
                    page.data["lat"])
                data += " | Timezone: %s" % page.data["timezone"]
                event["stdout"].write(data)
            else:
                event["stderr"].write("No geoip data found")
        else:
            raise utils.EventsResultsError()

    @utils.hook("received.command.rdns")
    def rdns(self, event):
        """
        :help: Do a reverse-DNS look up on an IPv4/IPv6 address
        :usage: <IP>
        :prefix: rDNS
        """
        ip = event["args_split"][0] if event["args"] else ""
        if not ip:
            line = event["target"].buffer.find(REGEX_IP)
            if line:
                ip = line.match
        if not ip:
            raise utils.EventError("No IP provided")

        try:
            hostname, alias, ips = socket.gethostbyaddr(ip)
        except (socket.herror, socket.gaierror) as e:
            raise utils.EventError(e.strerror)
        event["stdout"].write("(%s) %s" % (ips[0], hostname))
