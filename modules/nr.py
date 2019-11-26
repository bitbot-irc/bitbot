#--depends-on commands
#--require-config nre-api-key

import collections, re, time
from datetime import datetime, date
from collections import Counter

from src import ModuleManager, utils

from suds.client import Client
from suds import WebFault

# Note that this module requires the open *Staff Version* of the Darwin API
# You can register for an API key here: http://openldbsv.nationalrail.co.uk/
# We use this instead of the 'regular' version because it offers a *lot* more
# information.

URL = 'https://lite.realtime.nationalrail.co.uk/OpenLDBSVWS/wsdl.aspx?ver=2016-02-16'

class Module(ModuleManager.BaseModule):
    _name = "NR"
    _client = None

    PASSENGER_ACTIVITIES = ["U", "P", "R"]
    COLOURS = [utils.consts.LIGHTBLUE, utils.consts.GREEN,
        utils.consts.RED, utils.consts.CYAN, utils.consts.LIGHTGREY,
        utils.consts.ORANGE]

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
        except Exception as e:
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
        ut_now = datetime.now().timestamp()
        nonetime = {"orig": None, "datetime": None, "ut": 0,
                    "short": '    ', "prefix": '', "on_time": False,
                    "estimate": False, "status": 4, "schedule": False}
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
                times[a] = nonetime

        for k, a in times.items():
            if not a["orig"]: continue
            a["short"] = a["datetime"].strftime("%H%M") if len(a["orig"]) > 5 else a["orig"]
            a["shortest"] = "%02d" % a["datetime"].minute if -300 < a["ut"]-ut_now < 1800 else a["short"]
            a["prefix"] = k[2] + ("s" if k[0] == "s" else "")
            a["estimate"] = k[0] == "e"
            a["schedule"] = k[0] == "s"
            a["on_time"] = a["ut"] - times["s"+ k[1:]]["ut"] < 300
            a["status"] = 1 if a["on_time"] else 2
            if "a" + k[1:] in service: a["status"] = {"d": 0, "a": 3}[k[2]]
            if k[0] == "s": a["status"] = 4

        arr, dep = [times[a] for a in a_types if times[a]["ut"]], [times[a] for a in d_types if times[a]["ut"]]
        times["arrival"] = (arr + dep + [nonetime])[0]
        times["departure"] = (dep + arr + [nonetime])[0]
        times["a"], times["d"] = (arr + [nonetime])[0], (dep + [nonetime])[0]
        times["both"] = times["departure"]
        times["max_sched"] = {"ut": max(times["sta"]["ut"], times["std"]["ut"])}
        return times

    def activities(self, string): return [a+b.strip() for a,b in list(zip(*[iter(string)]*2)) if (a+b).strip()]

    def reduced_activities(self, string): return [a for a in self.activities(string) if a in self.PASSENGER_ACTIVITIES]

    @utils.hook("received.command.nrtrains", min_args=1)
    def trains(self, event):
        """
        :help: Get train/bus services for a station (Powered by NRE)
        :usage: <crs_id>
        """

        client = self.client
        colours = self.COLOURS

        schedule = {}

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
            "period": (120, lambda x: x.isdigit() and 1 <= int(x) <= 480, lambda x: int(x)),
            "nonpassenger": (False, lambda x: type(x)==type(True)),
            "time": ("", lambda x: len(x)==4 and x.isdigit()),
            "date": ("", lambda x: len(x)==10),
            "tops": (None, lambda x: len(x)<4 and x.isdigit()),
            "power": (None, lambda x: x.upper() in ["EMU", "DMU", "HST", "D", "E", "DEM"], lambda x: x.upper()),
            "crs": (False, lambda x: type(x)==type(True)),
            "st": (False, lambda x: type(x)==type(True))
            })

        if filter["errors"]:
            raise utils.EventError("Filter: " + filter["errors_summary"])

        if filter["inter"] and filter["type"]!="departure":
            raise utils.EventError("Filtering by intermediate stations is only "
                "supported for departures.")

        nr_filterlist = client.factory.create("filterList")
        if filter["inter"]: nr_filterlist.crs.append(filter["inter"])

        now = datetime.now()
        if filter["time"]:
            now = now.replace(hour=int(filter["time"][:2]))
            now = now.replace(minute=int(filter["time"][2:]))
        if filter["date"]:
            newdate = datetime.strptime(filter["date"], "%Y-%m-%d").date()
            now = now.replace(day=newdate.day, month=newdate.month, year=newdate.year)

        method = client.service.GetArrivalDepartureBoardByCRS if len(location_code) == 3 else client.service.GetArrivalDepartureBoardByTIPLOC
        try:
            query = method(100, location_code, now.isoformat().split(".")[0], filter["period"],
                nr_filterlist, "to", '', "PBS", filter["nonpassenger"])
        except WebFault as detail:
            if str(detail) == "Server raised fault: 'Invalid crs code supplied'":
                raise utils.EventError("Invalid CRS code.")
            else:
                raise utils.EventError("An error occurred.")

        nrcc_severe = len([a for a in query["nrccMessages"][0] if a["severity"] == "Major"]) if "nrccMessages" in query else 0
        if event.get("external"):
            station_summary = "%s (%s) - %s (%s):\n" % (query["locationName"], query["crs"], query["stationManager"],
                query["stationManagerCode"])
        else:
            severe_summary = ""
            if nrcc_severe:
                severe_summary += ", "
                severe_summary += utils.irc.bold(utils.irc.color("%s severe messages" % nrcc_severe, utils.consts.RED))
            station_summary = "%s (%s, %s%s)" % (query["locationName"], query["crs"], query["stationManagerCode"], severe_summary)

        if not "trainServices" in query and not "busServices" in query and not "ferryServices" in query:
            return event["stdout"].write("%s: No services for the next %s minutes" % (
                station_summary, filter["period"]))

        trains = []
        services = []
        if "trainServices" in query: services += query["trainServices"][0]
        if "busServices" in query: services += query["busServices"][0]
        if "ferryServices" in query: services += query["ferryServices"][0]
        for t in services:
            parsed = {
                "rid" : t["rid"],
                "uid" : t["uid"],
                "head" : t["trainid"],
                "platform": '?' if not "platform" in t else t["platform"],
                "platform_hidden": "platformIsHidden" in t and t["platformIsHidden"],
                "platform_prefix": "",
                "toc": t["operatorCode"],
                "cancelled" : t["isCancelled"] if "isCancelled" in t else False,
                "delayed"   : t["departureType"]=="Delayed" if "departureType" in t else None,
                "cancel_reason" : t["cancelReason"]["value"] if "cancelReason" in t else "",
                "delay_reason" : t["delayReason"]["value"] if "delayReason" in t else "",
                "terminating" : not "std" in t and not "etd" in t and not "atd" in t,
                "bus" : t["trainid"]=="0B00",
                "times" : self.process(t),
                "activity" : self.reduced_activities(t["activities"]),
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

            if parsed["cancelled"] or parsed["delayed"]:
                for k, time in parsed["times"].items():
                    time["short"], time["on_time"], time["status"], time["prefix"] = (
                        "%s:%s" % ("C" if parsed["cancel_reason"] else "D", parsed["cancel_reason"] or parsed["delay_reason"] or "?"),
                        False, 2, ""
                        )

            trains.append(parsed)


        for t in trains:
            t["dest_summary"] = "/".join(["%s%s" %(a["code"]*filter["crs"] or a["name"], " " + a["via"]
                if a["via"] else '') for a in t["destinations"]])
            t["origin_summary"] = "/".join(["%s%s" %(a["code"]*filter["crs"] or a["name"], " " + a["via"]
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
                filter["terminating"] and not train["terminating"],
                filter["tops"] and not filter["tops"] in train.get("tops_possible", []),
                filter["power"] and not filter["power"]==train.get("power_type", None),
            ]:
                train_locs_toc.append((train["destinations"], train["toc"]))
                trains_filtered.append(train)
        if event.get("external"):
            trains_string = "\n".join(["%-6s %-4s %-2s %-3s %1s%-6s %1s %s" % (
                t["uid"], t["head"], t["toc"], "bus" if t["bus"] else t["platform"],
                "~" if t["times"]["both"]["estimate"] else '',
                t["times"]["both"]["prefix"] + t["times"]["both"]["short"],
                "←" if t["terminating"] or filter["type"]=="arrival" else "→",
                t["origin_summary"] if t["terminating"] or filter["type"]=="arrival" else t["dest_summary"]
                ) for t in trains_filtered])
        else:
            trains_string = ", ".join(["%s%s (%s, %s%s%s%s, %s%s%s)" % (
                "from " if not filter["type"][0] in "ad" and t["terminating"] else '',
                t["origin_summary"] if t["terminating"] or filter["type"]=="arrival" else t["dest_summary"],
                t["uid"],
                t["platform_prefix"],
                "bus" if t["bus"] else t["platform"],
                "*" if t["platform_hidden"] else '',
                "?" if "platformsAreUnreliable" in query and query["platformsAreUnreliable"] else '',
                t["times"][filter["type"]]["prefix"].replace(filter["type"][0], '') if not t["cancelled"] else "",
                utils.irc.bold(utils.irc.color(t["times"][filter["type"]]["shortest"*filter["st"] or "short"], colours[t["times"][filter["type"]]["status"]])),
                bool(t["activity"])*", " + "+".join(t["activity"]),
                ) for t in trains_filtered])
        if event.get("external"):
            event["stdout"].write("%s%s\n%s" % (
                station_summary, "\n calling at %s" % filter["inter"] if filter["inter"] else '', trains_string))
        else:
            event["stdout"].write("%s%s: %s" % (station_summary, " departures calling at %s" % filter["inter"] if filter["inter"] else '', trains_string))

    @utils.hook("received.command.nrservice", min_args=1)
    def service(self, event):
        """
        :help: Get train service information for a UID, headcode or RID
            (Powered by NRE)
        :usage: <service_id>
        """
        client = self.client
        colours = self.COLOURS
        external = event.get("external", False)

        SCHEDULE_STATUS = {"B": "perm bus", "F": "freight train", "P": "train",
            "S": "ship", "T": "trip", "1": "train", "2": "freight",
            "3": "trip", "4": "ship", "5": "bus"}

        schedule = {}
        sources = []

        service_id = event["args_split"][0]

        filter = self.filter(' '.join(event["args_split"][1:]) if len(event["args_split"]) > 1 else "", {
            "passing": (False, lambda x: type(x)==type(True)),
            "associations": (False, lambda x: type(x)==type(True)),
            "type": ("arrival", lambda x: x in ["arrival", "departure"])
            })

        if filter["errors"]:
            raise utils.EventError("Filter: " + filter["errors_summary"])

        rid = service_id
        if len(service_id) <= 8:
            query = client.service.QueryServices(service_id, datetime.utcnow().date().isoformat(),
                datetime.utcnow().time().strftime("%H:%M:%S+0000"))
            if not query and not schedule:
                return event["stdout"].write("No service information is available for this identifier.")

            if query and len(query["serviceList"][0]) > 1:
                return event["stdout"].write("Identifier refers to multiple services: " +
                    ", ".join(["%s (%s->%s)" % (a["uid"], a["originCrs"], a["destinationCrs"]) for a in query["serviceList"][0]]))
            if query: rid = query["serviceList"][0][0]["rid"]

            if query:
                sources.append("LDBSVWS")
                query = client.service.GetServiceDetailsByRID(rid)
            if schedule:
                sources.append("Eagle/SCHEDULE")
                if not query: query = {"trainid": schedule["signalling_id"] or "0000", "operator": schedule["operator_name"] or schedule["atoc_code"]}
                stype = "%s %s" % (schedule_query.data["tops_inferred"], schedule["power_type"]) if schedule_query.data["tops_inferred"] else schedule["power_type"]
                for k,v in {
                    "operatorCode": schedule["atoc_code"],
                    "serviceType": stype if stype else SCHEDULE_STATUS[schedule["status"]],
                }.items():
                    query[k] = v

        disruptions = []
        if "cancelReason" in query:
            disruptions.append("Cancelled (%s%s)" % (query["cancelReason"]["value"], " at " + query["cancelReason"]["_tiploc"] if query["cancelReason"]["_tiploc"] else ""))
        if "delayReason" in query:
            disruptions.append("Delayed (%s%s)" % (query["delayReason"]["value"], " at " + query["delayReason"]["_tiploc"] if query["delayReason"]["_tiploc"] else ""))
        if disruptions and not external:
            disruptions = utils.irc.color(", ".join(disruptions), utils.consts.RED) + " "
        elif disruptions and external:
            disruptions = ", ".join(disruptions)
        else: disruptions = ""

        stations = []
        for station in query["locations"][0] if "locations" in query else schedule["locations"]:
            if "locations" in query:
                parsed = {"name": station["locationName"],
                    "crs": (station["crs"] if "crs" in station else station["tiploc"]).rstrip(),
                    "tiploc": station["tiploc"].rstrip(),
                    "called": "atd" in station,
                    "passing": station["isPass"] if "isPass" in station else False,
                    "first": len(stations) == 0,
                    "last" : False,
                    "cancelled" : station["isCancelled"] if "isCancelled" in station else False,
                    "associations": [],
                    "length": station["length"] if "length" in station else None,
                    "times": self.process(station),
                    "platform": station["platform"] if "platform" in station else None,
                    "activity": self.activities(station["activities"]) if "activities" in station else [],
                    "activity_p": self.reduced_activities(station["activities"]) if "activities" in station else [],
                    }

                if parsed["cancelled"]:
                    parsed["times"]["arrival"].update({"short": "Cancelled", "on_time": False, "status": 2})
                    parsed["times"]["departure"].update({"short": "Cancelled", "on_time": False, "status": 2})

                associations = station["associations"][0] if "associations" in station else []
                for assoc in associations:
                    parsed_assoc = {
                        "uid_assoc": assoc.uid,
                        "category": {"divide": "VV", "join": "JJ", "next": "NP"}[assoc["category"]],
                        "from": parsed["first"], "direction": assoc["destTiploc"].rstrip()==parsed["tiploc"],
                        "origin_name": assoc["origin"], "origin_tiploc": assoc["originTiploc"],
                        "origin_crs": assoc["originCRS"] if "originCRS" in assoc else None,

                        "dest_name": assoc["destination"], "dest_tiploc": assoc["destTiploc"],
                        "dest_crs": assoc["destCRS"] if "destCRS" in assoc else None,

                        "far_name": assoc["destination"], "far_tiploc": assoc["destTiploc"],
                        "far_crs": assoc["destCRS"] if "destCRS" in assoc else None,
                        }
                    if parsed_assoc["direction"]:
                        parsed_assoc.update({"far_name": parsed_assoc["origin_name"],
                            "far_tiploc": parsed_assoc["origin_tiploc"], "far_crs": parsed_assoc["origin_crs"]})
                    parsed["associations"].append(parsed_assoc)
            else:
                parsed = {"name": (station["name"] or "none"),
                    "crs": station["crs"] if station["crs"] else station["tiploc"],
                    "tiploc": station["tiploc"],
                    "called": False,
                    "passing": bool(station.get("pass")),
                    "first": len(stations) == 0,
                    "last" : False,
                    "cancelled" : False,
                    "length": None,
                    "times": self.process(station["dolphin_times"]),
                    "platform": station["platform"],
                    "associations": station["associations"] or [],
                    "activity": self.activities(station["activity"]),
                    "activity_p": self.reduced_activities(station["activity"]),
                    }
            stations.append(parsed)

        [a for a in stations if a["called"] or a["first"]][-1]["last"] = True

        for station in stations[0:[k for k,v in enumerate(stations) if v["last"]][0]]:
            if not station["first"]: station["called"] = True

        for station in stations:
            for assoc in station["associations"]:
                assoc["summary"] = "{arrow} {assoc[category]} {assoc[uid_assoc]} {dir_arrow} {assoc[far_name]} ({code})".format(assoc=assoc, arrow=assoc["from"]*"<-" or "->", dir_arrow=(assoc["direction"])*"<-" or "->", code=assoc["far_crs"] or assoc["far_tiploc"])

            if station["passing"]:
                station["times"]["arrival"]["status"], station["times"]["departure"]["status"] = 5, 5
            elif station["called"]:
                station["times"]["arrival"]["status"], station["times"]["departure"]["status"] = 0, 0

            station["summary"] = "%s%s (%s%s%s%s%s)%s" % (
                "*" * station["passing"],
                station["name"],
                station["crs"] + ", " if station["name"] != station["crs"] else '',
                station["length"] + " car, " if station["length"] and (station["first"] or station["associations"]) else '',
                ("~" if station["times"][filter["type"]]["estimate"] else '') +
                station["times"][filter["type"]]["prefix"].replace(filter["type"][0], ""),
                utils.irc.color(station["times"][filter["type"]]["short"], colours[station["times"][filter["type"]]["status"]]),
                ", "*bool(station["activity_p"]) + "+".join(station["activity_p"]),
                ", ".join([a["summary"] for a in station["associations"]] if filter["associations"] else ""),
                )
            station["summary_external"] = "%1s%-5s %1s%-5s %-3s %-3s %-3s %s%s" % (
                "~"*station["times"]["a"]["estimate"] + "s"*(station["times"]["a"]["schedule"]),
                station["times"]["a"]["short"],
                "~"*station["times"]["d"]["estimate"] + "s"*(station["times"]["d"]["schedule"]),
                station["times"]["d"]["short"],
                station["platform"] or '',
                ",".join(station["activity"]) or '',
                station["crs"] or station["tiploc"],
                station["name"],
                "\n" + "\n".join([a["summary"] for a in station["associations"]]) if station["associations"] else "",
                )

        stations_filtered = []
        for station in stations:
            if station["passing"] and not filter["passing"]: continue
            if station["called"] and filter["default"] and not external:
                if not station["first"] and not station["last"]:
                    continue

            stations_filtered.append(station)
            if station["first"] and not station["last"] and filter["default"] and not external:
                stations_filtered.append({"summary": "(...)", "summary_external": "(...)"})

        done_count = len([s for s in stations if s["called"]])
        total_count = len(stations)
        if external:
            event["stdout"].write("%s: %s\n%s%s (%s) %s %s\n\n%s" % (
                service_id, ", ".join(sources),
                disruptions + "\n" if disruptions else '',
                query["operator"], query["operatorCode"], query["trainid"], query["serviceType"],
                "\n".join([s["summary_external"] for s in stations_filtered])
                ))
        else:
            event["stdout"].write("%s%s %s %s (%s/%s): %s" % (disruptions, query["operatorCode"],
                query["trainid"], query["serviceType"],
                done_count, total_count,
                ", ".join([s["summary"] for s in stations_filtered])))

    @utils.hook("received.command.nrhead", min_args=1)
    def head(self, event):
        """
        :help: Get information for a given headcode/UID/RID (Powered by NRE)
        :usage: <headcode>
        """
        client = self.client
        service_id = event["args_split"][0]

        query = client.service.QueryServices(service_id, datetime.utcnow().date().isoformat(),
            datetime.utcnow().time().strftime("%H:%M:%S+0000"))

        if not query:
            raise utils.EventError("No currently running services match this "
                "identifier")

        services = query["serviceList"][0]
        if event.get("external"):
            event["stdout"].write("\n".join(["{a.uid:6} {a.trainid:4} {a.originName} ({a.originCrs}) → {a.destinationName} ({a.destinationCrs})".format(a=a) for a in services]))
        else:
            event["stdout"].write(", ".join(["h/%s r/%s u/%s rs/%s %s (%s) -> %s (%s)" % (a["trainid"], a["rid"], a["uid"], a["rsid"], a["originName"], a["originCrs"], a["destinationName"], a["destinationCrs"]) for a in services]))

    @utils.hook("received.command.nrcode", min_args=1)
    def service_code(self, event):
        """
        :help: Get the text for a given delay/cancellation code (Powered by NRE)
        :usage: <code>
        """

        client = self.client

        if not event["args"].isnumeric():
            raise utils.EventError("The delay/cancellation code must be a "
                "number")
        reasons = {a["code"]:(a["lateReason"], a["cancReason"]) for a in client.service.GetReasonCodeList()[0]}
        if event["args"] in reasons:
            event["stdout"].write("%s: %s" % (event["args"], " / ".join(reasons[event["args"]])))
        else:
            event["stdout"].write("This doesn't seem to be a valid reason code")
