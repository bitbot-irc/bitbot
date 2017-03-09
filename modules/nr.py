import collections, re, time
from datetime import datetime
from collections import Counter

import Utils

from suds.client import Client
from suds import WebFault

# Note that this module requires the open *Staff Version* of the Darwin API
# You can register for an API key here: http://openldbsv.nationalrail.co.uk/
# We use this instead of the 'regular' version because it offers a *lot* more
# information.

URL = 'https://lite.realtime.nationalrail.co.uk/OpenLDBSVWS/wsdl.aspx?ver=2016-02-16'

class Module(object):

    _name = "NR"
    def __init__(self, bot):
        self.bot = bot
        self._client = None
        bot.events.on("received").on("command").on("nrtrains"
            ).hook(self.arrivals, min_args=1,
            help="Get train information for a station (Powered by NRE)",
            usage="<crs_id>")
        bot.events.on("received").on("command").on("nrservice"
            ).hook(self.service, min_args=1,
            help="Get train service information for a UID, headcode or RID (Powered by NRE)",
            usage="<service_id>")
        bot.events.on("received").on("command").on("nrhead"
            ).hook(self.head, min_args=1,
            help="Get information for a given headcode/UID/RID (Powered by NRE)",
            usage="<headcode>")
        bot.events.on("received").on("command").on("nrcode"
            ).hook(self.service_code, min_args=1,
            help="Get the text for a given delay/cancellation code (Powered by NRE)",
            usage="<code>")

    @property
    def client(self):
        if self._client: return self._client
        try:
            token = self.bot.config["nre-api-key"]
            client = Client(URL)
            header_token = client.factory.create('ns2:AccessToken')
            header_token.TokenValue = token
            client.set_options(soapheaders=header_token)
            self._client = client
        except:
            pass
        return self._client

    def filter(self, args, defaults):
        args = re.findall(r"[^\s,]+", args)
        params = {}

        for arg in args:
            if ":" in arg:
                params[arg.split(":", 1)[0]] = arg.split(":", 1)[1]
            elif "=" in arg:
                params[arg.split("=", 1)[0]] = arg.split("=", 1)[1]
            else:
                params[arg.replace("!", "")] = '!' not in arg

        ret = {k: v[0] for k,v in defaults.items()}
        ret["default"] = True
        ret["errors"] = []

        for k,v in params.items():
            if not k in defaults.keys():
                ret["errors"].append((k, "Invalid parameter"))
                continue
            if not defaults[k][1](v):
                ret["errors"].append((v, 'Invalid value for "%s"' % k))
                continue
            ret["default"] = False
            ret[k] = v if len(defaults[k]) == 2 else defaults[k][2](v)
        ret["errors_summary"] = ", ".join(['"%s": %s' % (a[0], a[1]) for a in ret["errors"]])
        return ret

    def arrivals(self, event):
        client = self.client
        colours = [Utils.COLOR_LIGHTBLUE, Utils.COLOR_GREEN, Utils.COLOR_RED, Utils.COLOR_CYAN, Utils.COLOR_LIGHTGREY]

        location_code = event["args_split"][0].upper()
        filter = self.filter(' '.join(event["args_split"][1:]) if len(event["args_split"]) > 1 else "", {
            "dest": ('', lambda x: x.isalpha() and len(x)==3),
            "origin":('', lambda x: x.isalpha() and len(x)==3),
            "inter": ('', lambda x: x.isalpha() and len(x)==3, lambda x: x.upper()),
            "toc": ('', lambda x: x.isalpha() and len(x) == 2),
            "dedup": (False, lambda x: type(x)==type(True)),
            "plat": ('', lambda x: len(x) <= 3),
            "type": ("departures", lambda x: x in ["departures", "arrivals", "both"]),
            "terminating": (False, lambda x: type(x)==type(True)),
            "period": (120, lambda x: x.isdigit() and 1 <= int(x) <= 240, lambda x: int(x))
            })

        if filter["errors"]:
            return event["stderr"].write("Filter: " + filter["errors_summary"])

        if filter["inter"] and filter["type"]!="departures":
            return event["stderr"].write("Filtering by intermediate stations is only supported for departures.")

        nr_filterlist = client.factory.create("filterList")
        if filter["inter"]: nr_filterlist.crs.append(filter["inter"])

        method = client.service.GetArrivalDepartureBoardByCRS if len(location_code) == 3 else client.service.GetArrivalDepartureBoardByTIPLOC
        try:
            query = method(100, location_code, datetime.now().isoformat().split(".")[0], filter["period"],
                nr_filterlist, "to", '', "PBS", False)
        except WebFault as detail:
            if str(detail) == "Server raised fault: 'Invalid crs code supplied'":
                return event["stderr"].write("Invalid CRS code.")
            else:
                return event["stderr"].write("An error occurred.")

        nrcc_severe = len([a for a in query["nrccMessages"][0] if a["severity"] == "Major"]) if "nrccMessages" in query else 0

        station_summary = "%s (%s, %s%s)" % (query["locationName"], query["crs"], query["stationManagerCode"],
            ", %s%s severe messages%s" % (Utils.color(Utils.COLOR_RED), nrcc_severe, Utils.color(Utils.FONT_RESET)) if nrcc_severe else ""
            )

        if not "trainServices" in query and not "busServices" in query:
            return event["stdout"].write("%s: No services for the next %s minutes" % (
                station_summary, filter["period"]))

        trains = []

        for t in query["trainServices"][0] if "trainServices" in query else [] + query["busServices"][0] if "busServices" in query else []:
            parsed = {
                "scheduled": datetime.strptime(t["std"] if "std" in t else t["sta"], "%Y-%m-%dT%H:%M:%S"),
                "scheduled_type" : "departure" if "std" in t else "arrival",
                "scheduled_short": 'd' if "std" in t else "a",
                "arrived" : "ata" in t,
                "departed": "atd" in t,
                "rid" : t["rid"],
                "uid" : t["uid"],
                "head" : t["trainid"],
                "platform": "?" if not "platform" in t else t["platform"],
                "platform_hidden": "platformIsHidden" in t and t["platformIsHidden"],
                "toc": t["operatorCode"],
                "cancelled" : t["isCancelled"] if "isCancelled" in t else False,
                "cancel_reason" : t["cancelReason"]["value"] if "cancelReason" in t else "",
                "terminating" : not "std" in t and not "etd" in t and not "atd" in t,
                "bus" : t["trainid"]=="0B00"
                }
            parsed["destinations"] = [{"name": a["locationName"], "tiploc": a["tiploc"],
                "crs": a["crs"] if "crs" in a else '', "code": a["crs"] if "crs"
                in a else a["tiploc"], "via": a["via"] if "via" in a else ''}
                for a in t["destination"][0]]

            parsed["origins"] = [{"name": a["locationName"], "tiploc": a["tiploc"],
                "crs": a["crs"] if "crs" in a else '', "code": a["crs"] if "crs"
                in a else a["tiploc"], "via": a["via"] if "via" in a else ''}
                for a in t["origin"][0]]

            parsed["departure_only"] = location_code in [a["code"] for a in parsed["origins"]]

            parsed["arrival"] = datetime.strptime(t["eta"] if "eta" in t else t["ata"], "%Y-%m-%dT%H:%M:%S") if "eta" in t or "ata" in t else None
            parsed["departure"] = datetime.strptime(t["etd"] if "etd" in t else t["atd"], "%Y-%m-%dT%H:%M:%S") if "etd" in t or "atd" in t else None
            parsed["time"], parsed["timeprefix"] = [a for a in [(parsed["departure"], "d"), (parsed["arrival"], "a"), (parsed["scheduled"], parsed["scheduled_short"] + "s")] if a[0] != None][0]
            parsed["datetime"] = parsed["time"]

            if parsed["cancelled"]:
                parsed["time"], parsed["timeprefix"], parsed["prediction"] = ("Cancelled: %s" % parsed["cancel_reason"], '', False)
            else:
                parsed["time"] = parsed["time"].strftime("%H%M")

            parsed["on_time"] = parsed["datetime"] == parsed["scheduled"] and not parsed["cancelled"]

            parsed["status"] = 1 if parsed["on_time"] else 2
            if "s" in parsed["timeprefix"]: parsed["status"] = 4
            if parsed["departed"]: parsed["status"] = 3
            if parsed["arrived"]:  parsed["status"] = 0

            trains.append(parsed)

        for t in trains:
            t["dest_summary"] = "/".join(["%s%s" %(a["name"], " " + a["via"]
                if a["via"] else '') for a in t["destinations"]])
            t["origin_summary"] = "/".join(["%s%s" %(a["name"], " " + a["via"]
                if a["via"] else '') for a in t["origins"]])

        trains = sorted(trains, key=lambda t: t["scheduled"])

        trains_filtered = []
        train_locs_toc = []

        for train in trains:
            if not True in [
                (train["destinations"], train["toc"]) in train_locs_toc and (filter["dedup"] or filter["default"]),
                filter["dest"] and not filter["dest"].upper() in [a["code"] for a in train["destinations"]],
                filter["origin"] and not filter["origin"].upper() in [a["code"] for a in train["origins"]],
                filter["toc"] and not filter["toc"].upper() == train["toc"],
                filter["plat"] and not filter["plat"] == train["platform"],
                filter["type"] == "departures" and train["terminating"],
                filter["type"] == "arrivals" and train["departure_only"],
                filter["terminating"] and not train["terminating"]
            ]:
                train_locs_toc.append((train["destinations"], train["toc"]))
                trains_filtered.append(train)

        trains_string = ", ".join(["%s%s (%s, %s%s, %s%s%s%s)" % (
            "from " if not filter["type"] in ["arrivals", "departures"] and t["terminating"] else '',
            t["origin_summary"] if t["terminating"] or filter["type"]=="arrivals" else t["dest_summary"],
            t["uid"],
            "bus" if t["bus"] else t["platform"], "?" if t["platform_hidden"] else '',
            t["timeprefix"].replace(filter["type"][0], ""),
            Utils.color(colours[t["status"]]),
            t["time"],
            Utils.color(Utils.FONT_RESET)
            ) for t in trains_filtered])

        event["stdout"].write("%s (%s, %s%s)%s: %s" % (query["locationName"], query["crs"],
            query["stationManagerCode"],
            ", %s%s severe messages%s" % (Utils.color(Utils.COLOR_RED), nrcc_severe, Utils.color(Utils.FONT_RESET)) if nrcc_severe else "",
            " departures calling at %s" % filter["inter"] if filter["inter"] else '',
            trains_string))

    def service(self, event):
        client = self.client
        colours = [Utils.COLOR_LIGHTBLUE, Utils.COLOR_GREEN, Utils.COLOR_RED, Utils.COLOR_CYAN, Utils.COLOR_LIGHTGREY]

        service_id = event["args_split"][0]

        filter = self.filter(' '.join(event["args_split"][1:]) if len(event["args_split"]) > 1 else "", {
            "passing": (False, lambda x: type(x)==type(True))
            })

        if filter["errors"]:
            event["stderr"].write("Filter: " + filter["errors_summary"])
            return

        rid = service_id
        if len(service_id) <= 8:
            query = client.service.QueryServices(service_id, datetime.utcnow().date().isoformat(),
                datetime.utcnow().time().strftime("%H:%M:%S+0000"))
            if not query:
                return event["stdout"].write("No service information is available for this identifier.")
            if len(query["serviceList"][0]) > 1:
                return event["stdout"].write("Identifier refers to multiple services: " +
                    ", ".join(["%s (%s->%s)" % (a["uid"], a["originCrs"], a["destinationCrs"]) for a in query["serviceList"][0]]))
            rid = query["serviceList"][0][0]["rid"]

        query = client.service.GetServiceDetailsByRID(rid)

        disruptions = []
        if "cancelReason" in query:
            disruptions.append("Cancelled (%s%s)" % (query["cancelReason"]["value"], " at " + query["cancelReason"]["_tiploc"] if query["cancelReason"]["_tiploc"] else ""))
        if "delayReason" in query:
            disruptions.append("Delayed (%s%s)" % (query["delayReason"]["value"], " at " + query["delayReason"]["_tiploc"] if query["delayReason"]["_tiploc"] else ""))
        if disruptions:
            disruptions = Utils.color(Utils.COLOR_RED) + ", ".join(disruptions) + Utils.color(Utils.FONT_RESET) + " "
        else: disruptions = ""

        stations = []
        for station in query["locations"][0]:
            parsed = {"name": station["locationName"],
                "crs": (station["crs"] if "crs" in station else station["tiploc"]).rstrip(),
                "scheduled": datetime.strptime(station["sta"] if "sta" in station else station["std"], "%Y-%m-%dT%H:%M:%S"),
                "scheduled_type" : "arrival" if "sta" in station else "departure",
                "scheduled_short": '' if "sta" in station else "d",
                "called": "atd" in station or "ata" in station,
                "passing": station["isPass"] if "isPass" in station else False,
                "prediction": "eta" in station or "etd" in station and not "atd" in station,
                "first": len(stations) == 0,
                "last" : False,
                "cancelled" : station["isCancelled"] if "isCancelled" in station else False,
                "divide_summary": ""
                }
            parsed["arrival"] = datetime.strptime(station["eta"] if "eta" in station else station["ata"], "%Y-%m-%dT%H:%M:%S") if "eta" in station or "ata" in station else None
            parsed["departure"] = datetime.strptime(station["etd"] if "etd" in station else station["atd"], "%Y-%m-%dT%H:%M:%S") if "etd" in station or "atd" in station else None
            parsed["time"], parsed["timeprefix"] = [a for a in [(parsed["arrival"], ''), (parsed["departure"], "d"), (parsed["scheduled"], parsed["scheduled_short"] + "s")] if a[0] != None][0]
            parsed["datetime"] = parsed["time"]
            if parsed["cancelled"]:
                parsed["time"], parsed["timeprefix"], parsed["prediction"] = ("Cancelled", '', False)
            else:
                parsed["time"] = parsed["time"].strftime("%H%M")
            parsed["on_time"] = parsed["datetime"] == parsed["scheduled"] and not parsed["cancelled"]

            parsed["associations"] = {a["category"] : a for a in station["associations"][0]} if "associations" in station else {}
            parsed["divides"] = "divide" in parsed["associations"].keys()
            parsed["joins"] = "join" in parsed["associations"].keys()
            if parsed["divides"]:
                divide = parsed["associations"]["divide"]
                parsed["divide_summary"] = "%sDividing as %s to %s (%s)%s at " % (
                    Utils.color(Utils.FONT_BOLD),
                    divide["uid"], divide["destination"],
                    divide["destCRS"] if "destCRS" in divide else divide["destTiploc"],
                    Utils.color(Utils.FONT_RESET)
                    )
            if parsed["joins"]:
                divide = parsed["associations"]["join"]
                parsed["divide_summary"] = "%sJoining %s from %s (%s)%s at " % (
                    Utils.color(Utils.FONT_BOLD),
                    divide["uid"], divide["origin"],
                    divide["originCRS"] if "originCRS" in divide else divide["originTiploc"],
                    Utils.color(Utils.FONT_RESET)
                    )

            stations.append(parsed)

        [a for a in stations if a["called"] or a["first"]][-1]["last"] = True

        for station in stations[0:[k for k,v in enumerate(stations) if v["last"]][0]]:
            if not station["first"]: station["called"] = True

        for station in stations:
            station["status"] = 1 if station["on_time"] else 2
            if "s" in station["timeprefix"]: station["status"] = 4
            if station["called"]: station["status"] = 0
            if station["passing"]: station["status"] = 3

            station["summary"] = "%s%s%s(%s, %s%s%s%s)" % (
                station["divide_summary"],
                "*" if station["passing"] else '',
                station["name"] + " " if station["name"] != station["crs"] else '',
                station["crs"], ("~" if station["prediction"] else '') + station["timeprefix"],
                Utils.color(colours[station["status"]]),
                station["time"],
                Utils.color(Utils.FONT_RESET)
                )

        stations_filtered = []
        for station in stations:
            if station["passing"] and not filter["passing"]: continue
            if station["called"] and filter["default"]:
                if not station["first"] and not station["last"]:
                    continue

            stations_filtered.append(station)
            if station["first"] and not station["last"] and filter["default"]:
                stations_filtered.append({"summary": "(...)"})

        done_count = len([s for s in stations if s["called"]])
        total_count = len(stations)

        event["stdout"].write("%s%s %s %s (%s%s%s/%s/%s): %s" % (disruptions, query["operator"],
            query["trainid"], query["serviceType"],
            Utils.color(Utils.COLOR_LIGHTBLUE), done_count, Utils.color(Utils.FONT_RESET),
            len(stations_filtered), total_count,
            ", ".join([s["summary"] for s in stations_filtered])))

    def head(self, event):
        client = self.client
        service_id = event["args_split"][0]

        query = client.service.QueryServices(service_id, datetime.utcnow().date().isoformat(),
            datetime.utcnow().time().strftime("%H:%M:%S+0000"))
        event["stdout"].write(", ".join(["h/%s r/%s u/%s rs/%s %s (%s) -> %s (%s)" % (a["trainid"], a["rid"], a["uid"], a["rsid"], a["originName"], a["originCrs"], a["destinationName"], a["destinationCrs"]) for a in query["serviceList"][0]]))

    def service_code(self, event):
        client = self.client

        if not event["args"].isnumeric():
            return event["stderr"].write("The delay/cancellation code must be a number")
        reasons = {a["code"]:(a["lateReason"], a["cancReason"]) for a in client.service.GetReasonCodeList()[0]}
        if event["args"] in reasons:
            event["stdout"].write("%s: %s" % (event["args"], " / ".join(reasons[event["args"]])))
        else:
            event["stdout"].write("This doesn't seem to be a valid reason code")
