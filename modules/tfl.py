import datetime
import Utils

URL_BUS = "https://api.tfl.gov.uk/StopPoint/%s/Arrivals"
URL_BUS_SEARCH = "https://api.tfl.gov.uk/StopPoint/Search/%s"

class Module(object):
    _name = "TFL"
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("command").on("tflbus"
            ).hook(self.bus, min_args=1,
            help="Get bus due times for a TfL bus stop",
            usage="<stop_id>")

    def bus(self, event):
        app_id = self.bot.config["tfl-api-id"]
        app_key = self.bot.config["tfl-api-key"]
        stop_id = event["args_split"][0]
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
                    for i, bus in enumerate(busses):
                        if bus[-1] == 0:
                            bus[-1] = "due"
                        elif bus[-1] == 1:
                            bus[-1] = "in 1 minute"
                        else:
                            bus[-1] = "in %d minutes" % bus[-1]
                    event["stdout"].write("%s (%s): %s" % (stop_name, stop_id,
                        ", ".join(["%s (%s)" % (number, due) for number, due in busses]
                        )))
                else:
                    event["stderr"].write("%s: No busses due" % stop_id)
            else:
                event["stderr"].write("Bus ID '%s' unknown" % stop_id)
        else:
            event["stderr"].write("Please provide a numeric bus stop ID")
