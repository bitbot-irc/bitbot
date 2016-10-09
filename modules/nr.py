import collections, datetime, re, time
import Utils
from suds.client import Client

URL = 'https://lite.realtime.nationalrail.co.uk/OpenLDBWS/wsdl.aspx?2016-02-16'

class Module(object):
    _name = "NR"
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("command").on("nrtrains"
            ).hook(self.arrivals, min_args=1,
            help="Get train information for a station (Powered by NRE)",
            usage="<crs_id>")

    def time_compare(self, one, two):
        return (one.hour - two.hour) * 60 + (one.minute - two.minute)

    def span(self, gen, std, etd, human=True):
        expected = std
        if etd.replace(":", "").isdigit():
            expected = etd
        elif etd != "On time":
            return etd

        time_due = datetime.datetime.strptime(expected, "%H:%M")
        time_until = self.time_compare(time_due.time(), gen.time())

        if time_until == 0: human_time = "due"
        else: human_time = "in %s min" % time_until

        if human: return human_time
        else: return time_until

    def arrivals(self, event):
        token = self.bot.config["nre-api-key"]
        crs = event["args_split"][0]

        client = Client(URL)

        header_token = client.factory.create('ns2:AccessToken')
        header_token.TokenValue = token
        client.set_options(soapheaders=header_token)
        query = client.service.GetDepartureBoard(50, crs)

        trains = []

        for t in query["trainServices"][0]:
            trains.append({
                "estimated" : t["etd"],
                "scheduled" : t["std"],
                "time" : self.span(query["generatedAt"], t["std"], t["etd"]),
                "dest_name": t["destination"][0][0]["locationName"],
                "dest_id": t["destination"][0][0]["crs"],
#                "via": t["destination"][0][0]["via"],
                ""
                "via": "",
                "platform": "?" if not "platform" in t else t["platform"]
                })

        trains = sorted(trains, key=lambda t: int(t["scheduled"].replace(":", "")))

        trains_filtered = []
        train_dest_plat = []

        for train in trains:
            if (train["dest_name"] + train["via"], train["platform"]) in train_dest_plat: continue
            train_dest_plat.append((train["dest_name"] + train["via"], train["platform"]))
            trains_filtered.append(train)

        trains_string = ", ".join(["%s (plat %s, %s)" % (t["dest_name"], t["platform"], t["time"],
            ) for t in trains_filtered])

        event["stdout"].write("%s (%s): %s" % (query["locationName"], crs,
            trains_string))
