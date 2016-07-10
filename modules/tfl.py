import collections, datetime
import Utils

URL_BUS = "https://api.tfl.gov.uk/StopPoint/%s/Arrivals"
URL_BUS_SEARCH = "https://api.tfl.gov.uk/StopPoint/Search/%s"

URL_LINE = "https://api.tfl.gov.uk/Line/Mode/tube/Status"
LINE_NAMES = ["bakerloo", "central", "circle", "district", "hammersmith and city", "jubilee", "metropolitan", "piccadilly", "victoria", "waterloo and city"]

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

    def bus(self, event):
        app_id = self.bot.config["tfl-api-id"]
        app_key = self.bot.config["tfl-api-key"]
        stop_id = event["args_split"][0]
        target_bus_route = None
        if len(event["args_split"]) > 1:
            target_bus_route = event["args_split"][1].lower()
        if stop_id.isdigit():
            bus_search = Utils.get_url(URL_BUS_SEARCH % stop_id, get_params={
                "app_id": app_id, "app_key": app_key}, json=True)
            if bus_search["matches"]:
                bus_stop = bus_search["matches"][0]
                real_stop_id = bus_stop["id"]
                stop_name = bus_stop["name"]
                bus_stop = Utils.get_url(URL_BUS % real_stop_id, get_params={
                    "app_id": app_id, "app_key": app_key}, json=True)
                busses = []
                for bus in bus_stop:
                    bus_number = bus["lineName"]
                    bus_due_iso8601 = bus["expectedArrival"]
                    bus_due = datetime.datetime.strptime(bus_due_iso8601,
                        "%Y-%m-%dT%H:%M:%SZ")
                    time_until = bus_due-datetime.datetime.utcnow()
                    time_until = int(time_until.total_seconds()/60)
                    busses.append([bus_number, time_until])
                if busses:
                    busses = sorted(busses, key=lambda b: b[-1])
                    busses_formatted = collections.OrderedDict()
                    for bus_route, time_until in busses:
                        if bus_route in busses_formatted:
                            continue
                        if time_until == 0:
                            time_until = "due"
                        elif time_until == 1:
                            time_until = "in 1 minute"
                        else:
                            time_until = "in %d minutes" % time_until
                        if not target_bus_route or bus_route.lower() == target_bus_route:
                            busses_formatted[bus_route] = time_until
                    busses_string = ", ".join(["%s (%s)" % (bus_route, time_until
                        ) for bus_route, time_until in busses_formatted.items()])
                    event["stdout"].write("%s (%s): %s" % (stop_name, stop_id,
                        busses_string))
                else:
                    event["stderr"].write("%s: No busses due" % stop_id)
            else:
                event["stderr"].write("Bus ID '%s' unknown" % stop_id)
        else:
            event["stderr"].write("Please provide a numeric bus stop ID")

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
