from src import ModuleManager, utils

URL_GEOIP = "http://ip-api.com/json/%s"

class Module(ModuleManager.BaseModule):
    _name = "GeoIP"

    @utils.hook("received.command.geoip", min_args=1)
    def geoip(self, event):
        """
        :help: Get geoip data on a given IPv4/IPv6 address
        :usage: <IP>
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
