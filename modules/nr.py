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
    COLOURS = [Utils.COLOR_LIGHTBLUE, Utils.COLOR_GREEN, Utils.COLOR_RED, Utils.COLOR_CYAN, Utils.COLOR_LIGHTGREY, Utils.COLOR_ORANGE]
    def __init__(self, bot):
        self.bot = bot
        self._client = None
        bot.events.on("received").on("command").on("nrtrains"
            ).hook(self.trains, min_args=1,
            help="Get train/bus services for a station (Powered by NRE)",
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

    def process(self, service):
        times = {}
        a_types = ["eta", "ata", "sta"]
        d_types = ["etd", "atd", "std"]

        for a in a_types + d_types:
            if a in service and service[a]:
                times[a] = {"orig": service[a]}

                if len(service[a]) > 5:
                    times[a]["datetime"] = datetime.strptime(service[a], "%Y-%m-%dT%H:%M:%S")
                else:
                    times[a]["datetime"] = datetime.strptime(
                        datetime.now().date().isoformat() + "T" + service[a][:4],
                        "%Y-%m-%dT%H%M"
                    )
                times[a]["ut"] = times[a]["datetime"].timestamp()
            else:
                times[a] = {"orig": None, "datetime": None, "ut": 0,
                    "short": "None", "prefix": '', "on_time": False,
                    "estimate": False}

        for k, a in times.items():
            if not a["orig"]: continue
            a["short"] = a["datetime"].strftime("%H%M") if len(a["orig"]) > 5 else a["orig"]
            a["prefix"] = k[2] + ("s" if k[0] == "s" else "")
            a["estimate"] = k[0] == "e"
            a["on_time"] = a["ut"] - times["s"+ k[1:]]["ut"] < 300
            a["status"] = 1 if a["on_time"] else 2
            if "a" + k[1:] in service: a["status"] = {"d": 0, "a": 3}[k[2]]
            if k[0] == "s": a["status"] = 4

        times["arrival"] = [times[a] for a in a_types + d_types if times[a]["ut"]][0]
        times["departure"] = [times[a] for a in d_types + a_types if times[a]["ut"]][0]
        times["both"] = times["departure"]
        times["max_sched"] = {"ut": max(times["sta"]["ut"], times["std"]["ut"])}
        return times

    def trains(self, event):
        client = self.client
        colours = self.COLOURS

        location_code = event["args_split"][0].upper()
        filter = self.filter(' '.join(event["args_split"][1:]) if len(event["args_split"]) > 1 else "", {
            "dest": ('',  lambda x: x.isalpha() and len(x)==3),
            "origin":('', lambda x: x.isalpha() and len(x)==3),
            "inter": ('', lambda x: x.isalpha() and len(x)==3, lambda x: x.upper()),
            "toc": ('',   lambda x: x.isalpha() and len(x) == 2),
            "dedup": (False, lambda x: type(x)==type(True)),
            "plat": ('',     lambda x: len(x) <= 3),
            "type": ("departure", lambda x: x in ["departure", "arrival", "both"]),
            "terminating": (False, lambda x: type(x)==type(True)),
            "period": (120, lambda x: x.isdigit() and 1 <= int(x) <= 240, lambda x: int(x))
            })

        if filter["errors"]:
            return event["stderr"].write("Filter: " + filter["errors_summary"])

        if filter["inter"] and filter["type"]!="departure":
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
                "rid" : t["rid"],
                "uid" : t["uid"],
                "head" : t["trainid"],
                "platform": "?" if not "platform" in t else t["platform"],
                "platform_hidden": "platformIsHidden" in t and t["platformIsHidden"],
                "toc": t["operatorCode"],
                "cancelled" : t["isCancelled"] if "isCancelled" in t else False,
                "cancel_reason" : t["cancelReason"]["value"] if "cancelReason" in t else "",
                "terminating" : not "std" in t and not "etd" in t and not "atd" in t,
                "bus" : t["trainid"]=="0B00",
                "times" : self.process(t)
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

            if parsed["cancelled"]:
                for k, time in parsed["times"].items():
                    time["short"], time["on_time"], time["status"] = "Cancelled: %s" % parsed["cancel_reason"], False, 2

            trains.append(parsed)

        for t in trains:
            t["dest_summary"] = "/".join(["%s%s" %(a["name"], " " + a["via"]
                if a["via"] else '') for a in t["destinations"]])
            t["origin_summary"] = "/".join(["%s%s" %(a["name"], " " + a["via"]
                if a["via"] else '') for a in t["origins"]])

        trains = sorted(trains, key=lambda t: t["times"]["max_sched"]["ut"] if filter["type"]=="both" else t["times"]["st" + filter["type"][0]]["ut"])

        trains_filtered = []
        train_locs_toc = []

        for train in trains:
            if not True in [
                (train["destinations"], train["toc"]) in train_locs_toc and (filter["dedup"] or filter["default"]),
                filter["dest"] and not filter["dest"].upper() in [a["code"] for a in train["destinations"]],
                filter["origin"] and not filter["origin"].upper() in [a["code"] for a in train["origins"]],
                filter["toc"] and not filter["toc"].upper() == train["toc"],
                filter["plat"] and not filter["plat"] == train["platform"],
                filter["type"] == "departure" and train["terminating"],
                filter["type"] == "arrival" and train["departure_only"],
                filter["terminating"] and not train["terminating"]
            ]:
                train_locs_toc.append((train["destinations"], train["toc"]))
                trains_filtered.append(train)

        trains_string = ", ".join(["%s%s (%s, %s%s%s, %s%s%s%s)" % (
            "from " if not filter["type"][0] in "ad" and t["terminating"] else '',
            t["origin_summary"] if t["terminating"] or filter["type"]=="arrival" else t["dest_summary"],
            t["uid"],
            "bus" if t["bus"] else t["platform"],
            "*" if t["platform_hidden"] else '',
            "?" if "platformsAreUnreliable" in query and query["platformsAreUnreliable"] else '',
            t["times"][filter["type"]]["prefix"].replace(filter["type"][0], '') if not t["cancelled"] else "",
            Utils.color(colours[t["times"][filter["type"]]["status"]]),
            t["times"][filter["type"]]["short"],
            Utils.color(Utils.FONT_RESET)
            ) for t in trains_filtered])

        event["stdout"].write("%s%s: %s" % (station_summary, " departures calling at %s" % filter["inter"] if filter["inter"] else '', trains_string))

    def service(self, event):
        client = self.client
        colours = self.COLOURS

        SCHEDULE_STATUS = {"B": "perm bus", "F": "freight train", "P": "train",
            "S": "ship", "T": "trip", "1": "train", "2": "freight",
            "3": "trip", "4": "ship", "5": "bus"}

        eagle_key = self.bot.config["eagle-api-key"]
        eagle_url = self.bot.config["eagle-api-url"]
        schedule = {}

        service_id = event["args_split"][0]

        filter = self.filter(' '.join(event["args_split"][1:]) if len(event["args_split"]) > 1 else "", {
            "passing": (False, lambda x: type(x)==type(True)),
            "type": ("arrival", lambda x: x in ["arrival", "departure"])
            })

        if filter["errors"]:
            event["stderr"].write("Filter: " + filter["errors_summary"])
            return

        rid = service_id
        if len(service_id) <= 8:
            query = client.service.QueryServices(service_id, datetime.utcnow().date().isoformat(),
                datetime.utcnow().time().strftime("%H:%M:%S+0000"))
            if eagle_url:
                schedule_query = Utils.get_url("%s/schedule/%s/%s" % (eagle_url, service_id, datetime.now().date().isoformat()), json=True)
                schedule = schedule_query["current"]
            if not query and not schedule:
                return event["stdout"].write("No service information is available for this identifier.")

            if query and len(query["serviceList"][0]) > 1:
                return event["stdout"].write("Identifier refers to multiple services: " +
                    ", ".join(["%s (%s->%s)" % (a["uid"], a["originCrs"], a["destinationCrs"]) for a in query["serviceList"][0]]))
            if query: rid = query["serviceList"][0][0]["rid"]

            if query:
                query = client.service.GetServiceDetailsByRID(rid)
            if schedule:
                if not query: query = {"trainid": schedule["schedule_segment"]["signalling_id"]}
                for k,v in {
                    "operatorCode": schedule["atoc_code"],
                    "serviceType": "class " + schedule_query["tops_inferred"] if schedule_query["tops_inferred"] else SCHEDULE_STATUS.get(schedule["train_status"], "?"),
                }.items():
                    query[k] = v

        disruptions = []
        if "cancelReason" in query:
            disruptions.append("Cancelled (%s%s)" % (query["cancelReason"]["value"], " at " + query["cancelReason"]["_tiploc"] if query["cancelReason"]["_tiploc"] else ""))
        if "delayReason" in query:
            disruptions.append("Delayed (%s%s)" % (query["delayReason"]["value"], " at " + query["delayReason"]["_tiploc"] if query["delayReason"]["_tiploc"] else ""))
        if disruptions:
            disruptions = Utils.color(Utils.COLOR_RED) + ", ".join(disruptions) + Utils.color(Utils.FONT_RESET) + " "
        else: disruptions = ""

        stations = []
        for station in query["locations"][0] if "locations" in query else schedule["schedule_segment"]["schedule_location"]:
            if "locations" in query:
                parsed = {"name": station["locationName"],
                    "crs": (station["crs"] if "crs" in station else station["tiploc"]).rstrip(),
                    "called": "atd" in station,
                    "passing": station["isPass"] if "isPass" in station else False,
                    "first": len(stations) == 0,
                    "last" : False,
                    "cancelled" : station["isCancelled"] if "isCancelled" in station else False,
                    "divide_summary": "",
                    "length": station["length"] if "length" in station else None,
                    "times": self.process(station)
                    }

                if parsed["cancelled"]:
                    time["arrival"]["short"], time["arrival"]["on_time"], time["arrival"]["status"] = "Cancelled", False, 2

                parsed["associations"] = {a["category"] : a for a in station["associations"][0]} if "associations" in station else {}
                parsed["divides"] = "divide" in parsed["associations"].keys()
                parsed["joins"] = "join" in parsed["associations"].keys()
                if parsed["divides"]:
                    divide = parsed["associations"]["divide"]
                    parsed["divide_summary"] = "%sDividing %s %s to %s (%s)%s at " % (
                        Utils.color(Utils.FONT_BOLD),
                        "from" if parsed["first"] else "as",
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
            else:
                parsed = {"name": station["name"],
                    "crs": station["crs"] if station["crs"] else station["tiploc_code"],
                    "called": False,
                    "passing": station.get("pass", None),
                    "first": len(stations) == 0,
                    "last" : False,
                    "cancelled" : False,
                    "divide_summary": "",
                    "length": None,
                    "times": self.process(station["dolphin_times"])
                    }
            stations.append(parsed)

        [a for a in stations if a["called"] or a["first"]][-1]["last"] = True

        for station in stations[0:[k for k,v in enumerate(stations) if v["last"]][0]]:
            if not station["first"]: station["called"] = True

        for station in stations:
            if station["passing"]:
                station["times"]["arrival"]["status"], station["times"]["departure"]["status"] = 5, 5
            elif station["called"]:
                station["times"]["arrival"]["status"], station["times"]["departure"]["status"] = 0, 0

            station["summary"] = "%s%s%s (%s%s%s%s%s%s)" % (
                station["divide_summary"],
                "*" if station["passing"] else '',
                station["name"],
                station["crs"] + ", " if station["name"] != station["crs"] else '',
                station["length"] + " cars, " if station["length"] and (station["first"] or (station["last"]) or station["divide_summary"]) else '',
                ("~" if station["times"][filter["type"]]["estimate"] else '') +
                station["times"][filter["type"]]["prefix"].replace(filter["type"][0], ""),
                Utils.color(colours[station["times"][filter["type"]]["status"]]),
                station["times"][filter["type"]]["short"],
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

        event["stdout"].write("%s%s %s %s (%s%s%s/%s/%s): %s" % (disruptions, query["operatorCode"],
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
