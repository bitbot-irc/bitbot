import collections, re, time
from datetime import datetime
import Utils
from suds.client import Client
from collections import Counter

# Note that this module requires the open *Staff Version* of the Darwin API
# You can register for an API key here: http://openldbsv.nationalrail.co.uk/
# We use this instead of the 'regular' version because it offers a *lot* more
# information.

URL = 'https://lite.realtime.nationalrail.co.uk/OpenLDBSVWS/wsdl.aspx?ver=2016-02-16'

class Module(object):

    _name = "NR"
    def __init__(self, bot):
        self.bot = bot
        self.result_map = {}
        bot.events.on("received").on("command").on("nrtrains"
            ).hook(self.arrivals, min_args=1,
            help="Get train information for a station (Powered by NRE)",
            usage="<crs_id>")
        bot.events.on("received").on("command").on("nrservice"
            ).hook(self.service, min_args=1,
            help="Get train service information for a headcode or RID (Powered by NRE)",
            usage="<service_id>")
        bot.events.on("received").on("command").on("nrhead"
            ).hook(self.head, min_args=1,
            help="Get information for a given headcode (Powered by NRE)",
            usage="<headcode>")

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
        location_code = event["args_split"][0].upper()

        client = Client(URL)

        header_token = client.factory.create('ns2:AccessToken')
        header_token.TokenValue = token
        client.set_options(soapheaders=header_token)
        method = client.service.GetDepartureBoardByCRS if len(location_code) == 3 else client.service.GetDepartureBoardByTIPLOC
        query = method(50, location_code, datetime.now().isoformat().split(".")[0], 120,
            client.factory.create("filterList"), "to", '', "PBS", False)
        trains = []

        for t in query["trainServices"][0]:
            trains.append({
                "scheduled" : datetime.strptime(t["std"], "%Y-%m-%dT%H:%M:%S"),
                "called" : "atd" in t,
                "dest_name": t["destination"][0][0]["locationName"],
                "dest_id": t["destination"][0][0]["crs"] if "crs" in t["destination"][0][0] else "---",
                "rid" : t["rid"],
                "uid" : t["uid"],
                "head" : t["trainid"],
                "via": '' if not "via" in t["destination"][0][0] else t["destination"][0][0]["via"],
                "platform": "?" if not "platform" in t else t["platform"]
                })

            if "etd" in t or "atd" in t:
                trains[-1]["departure"] = datetime.strptime(t["etd"] if "etd" in t else t["atd"], "%Y-%m-%dT%H:%M:%S")
                trains[-1]["time"] = trains[-1]["departure"].strftime("%H%M")
            elif "isCancelled" in t and t["isCancelled"]:
                trains[-1]["departure"] = "Cancelled"
                trains[-1]["time"] = "Cancelled"
            else:
                trains[-1]["departure"] = t["departureType"]
                trains[-1]["time"] = t["departureType"]

            trains[-1]["on_time"] = trains[-1]["scheduled"] == trains[-1]["departure"]


        for t in trains:
            t["dest_via"] = t["dest_name"] + (" " if t["via"] else '') + t["via"]

        trains = sorted(trains, key=lambda t: t["scheduled"])


        trains_filtered = []
        train_dest_plat = []

        for train in trains:
            if (train["dest_name"] + train["via"], train["platform"]) in train_dest_plat: continue
            train_dest_plat.append((train["dest_name"] + train["via"], train["platform"]))
            trains_filtered.append(train)

        self.result_map[event["target"].id] = trains_filtered

        trains_string = ", ".join(["%s (%s, %s, %s%s%s)" % (t["dest_via"], t["uid"], t["platform"],
            Utils.color(Utils.COLOR_GREEN if t["on_time"] else Utils.COLOR_RED),
            t["time"],
            Utils.color(Utils.FONT_RESET)
            ) for t in trains_filtered])

        event["stdout"].write("%s (%s): %s" % (query["locationName"], query["crs"],
            trains_string))

    def service(self, event):
        colours = [Utils.COLOR_LIGHTBLUE, Utils.COLOR_GREEN, Utils.COLOR_RED, Utils.COLOR_CYAN]


        service_id = event["args_split"][0]
        filter = event["args_split"][1] if len(event["args_split"]) > 1 else ""

        token = self.bot.config["nre-api-key"]
        client = Client(URL)
        header_token = client.factory.create('ns2:AccessToken')
        header_token.TokenValue = token
        client.set_options(soapheaders=header_token)

        rid = service_id
        if len(service_id) <= 8:
            query = client.service.QueryServices(service_id, datetime.utcnow().date().isoformat(),
                datetime.utcnow().time().strftime("%H:%M:%S+0000"))
            if len(query["serviceList"][0]) > 1:
                event["stderr"].write("Headcode refers to multiple services: " +
                    ", ".join(["%s (%s->%s)" % (a["rid"], a["originCrs"], a["destinationCrs"]) for a in query["serviceList"][0]]))
                return
            rid = query["serviceList"][0][0]["rid"]

        query = client.service.GetServiceDetailsByRID(rid)

        stations = []
        for station in query["locations"][0]:
            stations.append(
                {"name": station["locationName"],
                 "crs": (station["crs"] if "crs" in station else station["tiploc"]).rstrip(),
                 "scheduled": datetime.strptime(station["sta"] if "sta" in station else station["std"], "%Y-%m-%dT%H:%M:%S"),
                 "scheduled_type" : "arrival" if "sta" in station else "departure",
                 "scheduled_short": '' if "sta" in station else "d",
                 "called": "atd" in station or "ata" in station,
                 "passing": station["isPass"] if "isPass" in station else False,
                 "prediction": "eta" in station or "etd" in station and not "atd" in station,
                 "first": len(stations) == 0,
                 "last" : False
                })
            stations[-1]["arrival"] = datetime.strptime(station["eta"] if "eta" in station else station["ata"], "%Y-%m-%dT%H:%M:%S") if "eta" in station or "ata" in station else None
            stations[-1]["departure"] = datetime.strptime(station["etd"] if "etd" in station else station["atd"], "%Y-%m-%dT%H:%M:%S") if "etd" in station or "atd" in station else None
            stations[-1]["time"], stations[-1]["timeprefix"] = [a for a in [(stations[-1]["arrival"], ''), (stations[-1]["departure"], "d"), (stations[-1]["scheduled"], stations[-1]["scheduled_short"] + "s")] if a[0] != None][0]
            stations[-1]["time"] = stations[-1]["time"].strftime("%H%M")

        [a for a in stations if a["called"] or a["first"]][-1]["last"] = True

        for station in stations[0:[(k,v) for k,v in enumerate(stations) if v["last"]][0][0]]:
            if not station["first"]: station["called"] = True

        for station in stations:
            station["on_time"] = station["time"] == "On time"

            station["status"] = 1 if station["on_time"] else 2
            if station["called"]: station["status"] = 0
            if station["passing"]: station["status"] = 3

            station["summary"] = "%s%s(%s, %s%s%s%s)" % (
                "*" if station["passing"] else '',
                station["name"] + " " if station["name"] != station["crs"] else '',
                station["crs"], ("~" if station["prediction"] else '') + station["timeprefix"],
                Utils.color(colours[station["status"]]),
                station["time"],
                Utils.color(Utils.FONT_RESET)
                )

        stations_filtered = []
        for station in stations:
            if station["passing"] and filter != "*": continue
            if station["called"] and filter != "*":
                if not station["first"] and not station["last"]:
                    continue
            stations_filtered.append(station)
            if station["first"] and not station["last"]:
                stations_filtered.append({"summary": "(...)"})

        done_count = len([s for s in stations if s["called"]])
        total_count = len(stations)

        event["stdout"].write("%s train (%s/%s/%s): %s" % (query["operator"],
            done_count, len(stations_filtered), total_count,
            ", ".join([s["summary"] for s in stations_filtered])))

    def head(self, event):
        service_id = event["args_split"][0]

        token = self.bot.config["nre-api-key"]
        client = Client(URL)
        header_token = client.factory.create('ns2:AccessToken')
        header_token.TokenValue = token
        client.set_options(soapheaders=header_token)

        query = client.service.QueryServices(service_id, datetime.utcnow().date().isoformat(),
            datetime.utcnow().time().strftime("%H:%M:%S+0000"))
        event["stdout"].write(", ".join(["h/%s r/%s u/%s rs/%s %s (%s) -> %s (%s)" % (a["trainid"], a["rid"], a["uid"], a["rsid"], a["originName"], a["originCrs"], a["destinationName"], a["destinationCrs"]) for a in query["serviceList"][0]]))
