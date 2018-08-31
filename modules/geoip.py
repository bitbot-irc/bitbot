import Utils

URL_GEOIP = "http://ip-api.com/json/%s"

class Module(object):
    _name = "GeoIP"
    def __init__(self, bot):
        bot.events.on("received").on("command").on("geoip").hook(
            self.geoip, min_args=1,
            help="Get geoip data on a given IPv4/IPv6 address",
            usage="<IP>")

    def geoip(self, event):
        page = Utils.get_url(URL_GEOIP % event["args_split"][0],
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
