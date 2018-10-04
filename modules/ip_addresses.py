import socket
from src import ModuleManager, utils

URL_GEOIP = "http://ip-api.com/json/%s"

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.dns", min_args=1)
    def dns(self, event):
        """
        :help: Get all addresses for a given hostname (IPv4/IPv6)
        :usage: <hostname>
        """
        event["stdout"].set_prefix("DNS")
        event["stderr"].set_prefix("DNS")
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
        """
        page = utils.http.get_url(URL_GEOIP % event["args_split"][0],
            json=True)
        event["stdout"].set_prefix("GeoIP")
        event["stderr"].set_prefix("GeoIP")
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

    @utils.hook("received.command.rdns", min_args=1)
    def rdns(self, event):
        """
        :help: Do a reverse-DNS look up on an IPv4/IPv6 address
        :usage: <IP>
        """
        event["stdout"].set_prefix("rDNS")
        event["stderr"].set_prefix("rDNS")
        try:
            hostname, alias, ips = socket.gethostbyaddr(event["args_split"][0])
        except socket.herror as e:
            event["stderr"].write(str(e))
            return
        event["stdout"].write("%s: %s" % (ips[0], hostname))
