import re, socket
from src import ModuleManager, utils

URL_GEOIP = "http://ip-api.com/json/%s"
REGEX_IP = ("(?:\b|\s|^)((?:(?:[a-f0-9]{1,4}:){2,}|::)[^\s]+)(?:\b|\s|$)" # ipv6
    "|"
    "((?:\d{1,3}\.){3}\d{1,3})") # ipv4
REGEX_IP = re.compile(REGEX_IP, re.I)

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.dns", min_args=1)
    def dns(self, event):
        """
        :help: Get all addresses for a given hostname (IPv4/IPv6)
        :usage: <hostname>
        :prefix: DNS
        """
        hostname = event["args_split"][0]
        try:
            address_info = socket.getaddrinfo(hostname, 1, 0,
                socket.SOCK_DGRAM)
        except socket.gaierror:
            event["stderr"].write("Failed to find hostname")
            return
        ips = []
        for _, _, _, _, address in address_info:
            ips.append(address[0])
        event["stdout"].write("%s: %s" % (hostname, ", ".join(ips)))


    @utils.hook("received.command.geoip", min_args=1)
    def geoip(self, event):
        """
        :help: Get geoip data on a given IPv4/IPv6 address
        :usage: <IP>
        :prefix: GeoIP
        """
        page = utils.http.get_url(URL_GEOIP % event["args_split"][0],
            json=True)
        if page:
            if page["status"] == "success":
                data  = page["query"]
                data += " | Organisation: %s" % page["org"]
                data += " | City: %s" % page["city"]
                data += " | Region: %s (%s)" % (page["regionName"],
                    page["countryCode"])
                data += " | ISP: %s" % page["isp"]
                data += " | Lon/Lat: %s/%s" % (page["lon"],
                    page["lat"])
                data += " | Timezone: %s" % page["timezone"]
                event["stdout"].write(data)
            else:
                event["stderr"].write("No geoip data found")
        else:
            event["stderr"].write("Failed to load results")

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
                match = REGEX_IP.search(line.message)
                ip = match.group(1) or match.group(2)
        if not ip:
            event["stderr"].write("No IP provided")
            return

        print(ip)
        try:
            hostname, alias, ips = socket.gethostbyaddr(ip)
        except (socket.herror, socket.gaierror) as e:
            event["stderr"].write(e.strerror)
            return
        event["stdout"].write("%s: %s" % (ips[0], hostname))
