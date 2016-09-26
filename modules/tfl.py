import collections, datetime, re
import Utils

URL_BUS = "https://api.tfl.gov.uk/StopPoint/%s/Arrivals"
URL_BUS_SEARCH = "https://api.tfl.gov.uk/StopPoint/Search/%s"

URL_LINE = "https://api.tfl.gov.uk/Line/Mode/tube/Status"
LINE_NAMES = ["bakerloo", "central", "circle", "district", "hammersmith and city", "jubilee", "metropolitan", "piccadilly", "victoria", "waterloo and city"]

URL_STOP = "https://api.tfl.gov.uk/StopPoint/%s"
URL_STOP_SEARCH = "https://api.tfl.gov.uk/StopPoint/Search/%s"

URL_VEHICLE = "https://api.tfl.gov.uk/Vehicle/%s/Arrivals"

class Module(object):
    _name = "TFL"
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("command").on("tflbus"
            ).hook(self.bus, min_args=1,
            help="Get bus due times for a TfL bus stop",
            usage="<stop_id>")
        bot.events.on("received").on("command").on("tflline"
            ).hook(self.line,
            help="Get line status for TfL underground lines",
            usage="<line_name>")
        bot.events.on("received").on("command").on("tflsearch"
            ).hook(self.search, min_args=1,
            help="Get a list of TfL stop IDs for a given name",
            usage="<name>")
        bot.events.on("received").on("command").on("tflvehicle"
            ).hook(self.vehicle, min_args=1,
            help="Get information for a given vehicle",
            usage="<ID>")

    def bus(self, event):
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
            bus_search = Utils.get_url(URL_BUS_SEARCH % stop_id, get_params={
                "app_id": app_id, "app_key": app_key}, json=True)
            bus_stop = bus_search["matches"][0]
            real_stop_id = bus_stop["id"]
            stop_name = bus_stop["name"]
        else:
            bus_stop = Utils.get_url(URL_STOP % stop_id, get_params={
                "app_id": app_id, "app_key": app_key}, json=True)
            if bus_stop:
                real_stop_id = stop_id
                stop_name = bus_stop["commonName"]

        if real_stop_id:
            bus_stop = Utils.get_url(URL_BUS % real_stop_id, get_params={
                "app_id": app_id, "app_key": app_key}, json=True)
            busses = []
            for bus in bus_stop:
                bus_number = bus["lineName"]
                bus_due_iso8601 = bus["expectedArrival"]
                if "." in bus_due_iso8601:
                    bus_due_iso8601 = bus_due_iso8601.split(".")[0]+"Z"
                bus_due = datetime.datetime.strptime(bus_due_iso8601,
                    "%Y-%m-%dT%H:%M:%SZ")
                time_until = bus_due-datetime.datetime.utcnow()
                time_until = int(time_until.total_seconds()/60)

                # Nice human friendly time (also consistent with how TfL display it)
                if time_until == 0: human_time = "due"
                elif time_until == 1: human_time = "in 1 minute"
                else: human_time = "in %d minutes" % time_until

                # If the mode is "tube", "Underground Station" is redundant
                destination = bus.get("destinationName", "?")
                if (bus["modeName"] == "tube"): destination = destination.replace(" Underground Station", "")

                busses.append({"route": bus_number, "time": time_until, "id": bus["vehicleId"],
                    "destination": destination, "human_time": human_time,
                    "mode" : bus["modeName"]})
            if busses:
                busses = sorted(busses, key=lambda b: b["time"])
                busses_filtered = []
                bus_routes = []

                # dedup if target route isn't "*", filter if target route isn't None or "*"
                for b in busses:
                    if target_bus_route != "*":
                        if b["route"] in bus_routes: continue
                        bus_routes.append(b["route"])
                        if b["route"] == target_bus_route or not target_bus_route:
                            busses_filtered.append(b)
                    else:
                        busses_filtered.append(b)

                # do the magic formatty things!
                busses_string = ", ".join(["%s (%s, %s)" % (b["destination"], b["route"], b["human_time"]
                    ) for b in busses_filtered])
                event["stdout"].write("%s (%s): %s" % (stop_name, stop_id,
                    busses_string))
            else:
                event["stderr"].write("%s: No busses due" % stop_id)
        else:
           event["stderr"].write("Bus ID '%s' unknown" % stop_id)

    def line(self, event):
        app_id = self.bot.config["tfl-api-id"]
        app_key = self.bot.config["tfl-api-key"]

        lines = Utils.get_url(URL_LINE, get_params={
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

    def search(self, event):
        app_id = self.bot.config["tfl-api-id"]
        app_key = self.bot.config["tfl-api-key"]
        stop_name = event["args"]
        stop_search = Utils.get_url(URL_STOP_SEARCH % stop_name, get_params={
            "app_id": app_id, "app_key": app_key, "maxResults": "6", "faresOnly": "False"}, json=True)
        if stop_search:
            for stop in stop_search["matches"]:
                print(stop)
            results = ["%s (%s): %s" % (stop["name"], ", ".join(stop["modes"]), stop["id"]) for stop in stop_search["matches"]]
            event["stdout"].write("; ".join(results))
            if not results:
                event["stderr"].write("No results")
        else:
            event["stderr"].write("No results")

    def vehicle(self, event):
        app_id = self.bot.config["tfl-api-id"]
        app_key = self.bot.config["tfl-api-key"]

        vehicle_id = event["args_split"][0]

        vehicle = Utils.get_url(URL_VEHICLE % vehicle_id, get_params={
                "app_id": app_id, "app_key": app_key}, json=True)[0]

        #Stolen from bus
        vehicle_due_iso8601 = vehicle["expectedArrival"]
        if "." in vehicle_due_iso8601:
            vehicle_due_iso8601 = vehicle_due_iso8601.split(".")[0]+"Z"
        vehicle_due = datetime.datetime.strptime(vehicle_due_iso8601,
            "%Y-%m-%dT%H:%M:%SZ")
        time_until = vehicle_due-datetime.datetime.utcnow()
        time_until = int(time_until.total_seconds()/60)

        if time_until == 0: human_time = "due"
        elif time_until == 1: human_time = "in 1 minute"
        else: human_time = "in %d minutes" % time_until

        platform = vehicle["platformName"]

        p = re.compile("(.*) - Platform (\\d+)")
        m = p.match(platform)
        if m:
            platform = "platform %s (%s)" % (m.group(2), m.group(1))
        ###

        event["stdout"].write("%s (%s) to %s. %s. Arrival at %s (%s) %s on %s" % (
            vehicle["vehicleId"], vehicle["lineName"], vehicle["destinationName"], vehicle["currentLocation"],
                vehicle["stationName"], vehicle["naptanId"], human_time, platform))

