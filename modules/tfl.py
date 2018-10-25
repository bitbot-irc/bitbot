import collections, datetime, re
from src import ModuleManager, utils

URL_BUS = "https://api.tfl.gov.uk/StopPoint/%s/Arrivals"
URL_BUS_SEARCH = "https://api.tfl.gov.uk/StopPoint/Search/%s"

URL_LINE_ARRIVALS = "https://api.tfl.gov.uk/Line/%s/Arrivals"

URL_LINE = "https://api.tfl.gov.uk/Line/Mode/tube/Status"
LINE_NAMES = ["bakerloo", "central", "circle", "district", "hammersmith and city", "jubilee", "metropolitan", "piccadilly", "victoria", "waterloo and city"]

URL_STOP = "https://api.tfl.gov.uk/StopPoint/%s"
URL_STOP_SEARCH = "https://api.tfl.gov.uk/StopPoint/Search/%s"

URL_VEHICLE = "https://api.tfl.gov.uk/Vehicle/%s/Arrivals"

URL_ROUTE = "https://api.tfl.gov.uk/Line/%s/Route/Sequence/all?excludeCrowding=True"

PLATFORM_TYPES = ["Northbound", "Southbound", "Eastbound", "Westbound", "Inner Rail", "Outer Rail"]

class Module(ModuleManager.BaseModule):
    _name = "TFL"
    result_map = {}

    def vehicle_span(self, arrival_time, human=True):
        vehicle_due_iso8601 = arrival_time
        if "." in vehicle_due_iso8601:
            vehicle_due_iso8601 = vehicle_due_iso8601.split(".")[0]+"Z"
        vehicle_due = datetime.datetime.strptime(vehicle_due_iso8601,
            "%Y-%m-%dT%H:%M:%SZ")
        time_until = vehicle_due-datetime.datetime.utcnow()
        time_until = int(time_until.total_seconds()/60)

        if time_until == 0: human_time = "due"
        else: human_time = "in %s min" % time_until

        if human: return human_time
        else: return time_until

    def platform(self, platform, short=False):
        p = re.compile("(?:(.*) - Platform (\\d+)|(.*bound) Platform (\\d+))")
        m = p.match(platform)
        if m:
            platform = "platform %s (%s)" % (m.group(2), m.group(1))
            if short and m.group(1) in PLATFORM_TYPES:
                platform = m.group(2)
        return platform

    @utils.hook("received.command.tflbus", min_args=1)
    def bus(self, event):
        """
        :help: Get bus due times for a TfL bus stop
        :usage: <stop_id>
        """
        app_id = self.bot.config["tfl-api-id"]
        app_key = self.bot.config["tfl-api-key"]
        stop_id = event["args_split"][0]
        target_bus_route = None
        if len(event["args_split"]) > 1:
            target_bus_route = event["args_split"][1].lower()

        bus_stop = None
        real_stop_id = ""
        stop_name = ""
        if stop_id.isdigit():
            bus_search = utils.http.get_url(URL_BUS_SEARCH % stop_id,
                get_params={"app_id": app_id, "app_key": app_key},
                json=True)
            bus_stop = bus_search["matches"][0]
            real_stop_id = bus_stop["id"]
            stop_name = bus_stop["name"]
        else:
            bus_stop = utils.http.get_url(URL_STOP % stop_id,
                get_params={"app_id": app_id, "app_key": app_key},
                json=True)
            if bus_stop:
                real_stop_id = stop_id
                stop_name = bus_stop["commonName"]

        if real_stop_id:
            bus_stop = utils.http.get_url(URL_BUS % real_stop_id,
                get_params={"app_id": app_id, "app_key": app_key},
                json=True)
            busses = []
            for bus in bus_stop:
                bus_number = bus["lineName"]
                human_time = self.vehicle_span(bus["expectedArrival"])
                time_until = self.vehicle_span(bus["expectedArrival"], human=False)

                # If the mode is "tube", "Underground Station" is redundant
                destination = bus.get("destinationName", "?")
                if (bus["modeName"] == "tube"): destination = destination.replace(" Underground Station", "")

                busses.append({"route": bus_number, "time": time_until, "id": bus["vehicleId"],
                    "destination": destination, "human_time": human_time, "mode": bus["modeName"],
                    "platform": bus["platformName"],
                    "platform_short" : self.platform(bus["platformName"], short=True)})
            if busses:
                busses = sorted(busses, key=lambda b: b["time"])
                busses_filtered = []
                bus_route_dest = []
                bus_route_plat = []

                # dedup if target route isn't "*", filter if target route isn't None or "*"
                for b in busses:
                    if target_bus_route != "*":
                        if (b["route"], b["destination"]) in bus_route_dest: continue
                        if bus_route_plat.count((b["route"], b["platform"])) >= 2: continue
                        bus_route_plat.append((b["route"], b["platform"]))
                        bus_route_dest.append((b["route"], b["destination"]))
                        if b["route"] == target_bus_route or not target_bus_route:
                            busses_filtered.append(b)
                    else:
                        busses_filtered.append(b)

                self.result_map[event["target"].id] = busses_filtered

                # do the magic formatty things!
                busses_string = ", ".join(["%s (%s, %s)" % (b["destination"], b["route"], b["human_time"],
                    ) for b in busses_filtered])

                event["stdout"].write("%s (%s): %s" % (stop_name, stop_id,
                    busses_string))
            else:
                event["stderr"].write("%s: No busses due" % stop_id)
        else:
           event["stderr"].write("Bus ID '%s' unknown" % stop_id)

    @utils.hook("received.command.tflline")
    def line(self, event):
        """
        :help: Get line status for TfL underground lines
        :usage: <line_name>
        """
        app_id = self.bot.config["tfl-api-id"]
        app_key = self.bot.config["tfl-api-key"]

        lines = utils.http.get_url(URL_LINE, get_params={
                "app_id": app_id, "app_key": app_key}, json=True)
        statuses = []
        for line in lines:
            for status in line["lineStatuses"]:
                entry = {
                        "id": line["id"],
                        "name": line["name"],
                        "severity": status["statusSeverity"],
                        "description": status["statusSeverityDescription"],
                        "reason": status.get("reason")
                        }
                statuses.append(entry)
        statuses = sorted(statuses, key=lambda line: line["severity"])
        combined = collections.OrderedDict()
        for status in statuses:
            if not status["description"] in combined:
                combined[status["description"]] = []
            combined[status["description"]].append(status)
        result = ""
        for k, v in combined.items():
            result += k + ": "
            result += ", ".join(status["name"] for status in v)
            result += "; "
        if event["args"]:
            result = ""
            for status in statuses:
                for arg in event["args_split"]:
                    if arg.lower() in status["name"].lower():
                        result += "%s: %s (%d) '%s'; " % (status["name"], status["description"], status["severity"], status["reason"])
        if result:
            event["stdout"].write(result[:-2])
        else:
            event["stderr"].write("No results")

    @utils.hook("received.command.tflsearch", min_args=1)
    def search(self, event):
        """
        :help: Get a list of TfL stop IDs for a given name
        :usage: <name>
        """
        app_id = self.bot.config["tfl-api-id"]
        app_key = self.bot.config["tfl-api-key"]

        #As awful as this is, it also makes it ~work~.
        stop_name = event["args"].replace(" ", "%20")

        stop_search = utils.http.get_url(URL_STOP_SEARCH % stop_name, get_params={
            "app_id": app_id, "app_key": app_key, "maxResults": "6", "faresOnly": "False"}, json=True)
        if stop_search:
            for stop in stop_search["matches"]:
                pass
            results = ["%s (%s): %s" % (stop["name"], ", ".join(stop["modes"]), stop["id"]) for stop in stop_search["matches"]]
            event["stdout"].write("[%s results] %s" % (stop_search["total"], "; ".join(results)))
        else:
            event["stderr"].write("No results")

    @utils.hook("received.command.tflvehicle", min_args=1)
    def vehicle(self, event):
        """
        :help: Get information for a given vehicle
        :usage: <ID>
        """
        app_id = self.bot.config["tfl-api-id"]
        app_key = self.bot.config["tfl-api-key"]

        vehicle_id = event["args_split"][0]

        vehicle = utils.http.get_url(URL_VEHICLE % vehicle_id, get_params={
                "app_id": app_id, "app_key": app_key}, json=True)[0]

        arrival_time = self.vehicle_span(vehicle["expectedArrival"], human=False)
        platform = self.platform(vehicle["platformName"])

        event["stdout"].write("%s (%s) to %s. %s. Arrival at %s (%s) in %s minutes on %s" % (
            vehicle["vehicleId"], vehicle["lineName"], vehicle["destinationName"], vehicle["currentLocation"],
                vehicle["stationName"], vehicle["naptanId"], arrival_time, platform))

    @utils.hook("received.command.tflservice", min_args=1)
    def service(self, event):
        """
        :help: Get service information and arrival estimates
        :usage: <service index>
        """
        app_id = self.bot.config["tfl-api-id"]
        app_key = self.bot.config["tfl-api-key"]

        service_id = event["args_split"][0]

        if service_id.isdigit():
            if not event["target"].id in self.result_map:
                event["stdout"].write("No history")
                return
            results = self.result_map[event["target"].id]
            if int(service_id) >= len(results):
                event["stdout"].write("%s is too high. Remember that the first arrival is 0" % service_id)
                return
            service = results[int(service_id)]
        arrivals = utils.http.get_url(URL_LINE_ARRIVALS % service["route"],
            get_params={"app_id": app_id, "app_key": app_key}, json=True)

        arrivals = [a for a in arrivals if a["vehicleId"] == service["id"]]
        arrivals = sorted(arrivals, key=lambda b: b["timeToStation"])

        event["stdout"].write(
            "%s (%s) to %s: " % (arrivals[0]["vehicleId"], arrivals[0]["lineName"], arrivals[0]["destinationName"]) +
            ", ".join(["%s (%s, %s)" %
            (a["stationName"], self.platform(a.get("platformName", "?"), True),
            a["expectedArrival"][11:16]
            ) for a in arrivals]))

    @utils.hook("received.command.tflstop", min_args=1)
    def stop(self, event):
        """
        :help: Get information for a given stop
        :usage: <stop_id>
        """
        app_id = self.bot.config["tfl-api-id"]
        app_key = self.bot.config["tfl-api-key"]

        stop_id = event["args_split"][0]

        stop = utils.http.get_url(URL_STOP % stop_id, get_params={
            "app_id": app_id, "app_key": app_key}, json=True)

    def route(self, event):
        app_id = self.bot.config["tfl-api-id"]
        app_key = self.bot.config["tfl-api-key"]

        route_id = event["args_split"][0]

        route = utils.http.get_url(URL_ROUTE % route_id, get_params={
            "app_id": app_id, "app_key": app_key}, json=True)

        event["stdout"].write("")
