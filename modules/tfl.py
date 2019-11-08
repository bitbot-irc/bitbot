#--depends-on commands

import collections, urllib.parse
from src import ModuleManager, utils

URL_LINE = "https://api.tfl.gov.uk/Line/Mode/tube/Status"

URL_STOP_SEARCH = "https://api.tfl.gov.uk/StopPoint/Search/%s"
URL_STOP_ARRIVALS = "https://api.tfl.gov.uk/StopPoint/%s/Arrivals"

LINES = {
    "waterloo and city": "waterloo-city",
    "waterloo & city": "waterloo-city",
    "hammersmith and city": "hammersmith-city",
    "hammersmith & city": "hammersmith-city"
}

GOOD_COLOR = utils.irc.color("Good service", utils.consts.GREEN)
BAD_COLOR = utils.irc.color("Issues", utils.consts.ORANGE)

class Module(ModuleManager.BaseModule):
    _name = "TFL"


    @utils.hook("received.command.tubeline")
    @utils.kwarg("help", "Show status of Tube lines")
    @utils.kwarg("usage", "[line]")
    def line(self, event):
        lines = utils.http.request(URL_LINE, json=True)

        if event["args_split"]:
            line_query = event["args"].strip().lower()
            line_query = LINES.get(line_query, line_query)

            found = None
            for line in lines.data:
                if line["id"] == line_query:
                    found = line
                    break
            if found:
                status = found["lineStatuses"][0]
                reason = None
                if "reason" in status:
                    reason = " (%s)" % status["reason"].strip()

                event["stdout"].write("%s status: %s%s" % (
                    found["name"], status["statusSeverityDescription"], reason))
            else:
                event["stderr"].write("Unknown line '%s'" % line_query)
        else:
            good = []
            bad = []
            for line in lines.data:
                status = line["lineStatuses"][0]
                if status["statusSeverity"] == 10:
                    good.append(line["name"])
                else:
                    bad.append(line["name"])

            good_str = ", ".join(good)
            bad_str = ", ".join(bad)
            if good and bad:
                event["stdout"].write("%s: %s | %s: %s" %
                    (GOOD_COLOR, good_str, BAD_COLOR, bad_str))
            elif good:
                event["stdout"].write("%s on all lines" % GOOD_COLOR)
            else:
                event["stdout"].write("%s reported on all lines" % BAD_COLOR)

    @utils.hook("received.command.tubestop")
    @utils.kwarg("help", "Show arrivals for a given Tube station")
    @utils.kwarg("usage", "<station>")
    def stop(self, event):
        query = event["args"].strip()
        station = utils.http.request(
            URL_STOP_SEARCH % urllib.parse.quote(query), json=True)

        if station.data["matches"]:
            station = station.data["matches"][0]
            arrivals = utils.http.request(URL_STOP_ARRIVALS % station["id"],
                json=True)
            destinations = collections.OrderedDict()
            now = utils.datetime_utcnow().replace(second=0, microsecond=0)
            print(now.isoformat())

            arrivals = sorted(arrivals.data, key=lambda a: a["expectedArrival"])
            for train in arrivals:
                destination = train["destinationNaptanId"]
                if not destination in destinations:
                    arrival = utils.iso8601_parse(train["expectedArrival"])
                    if now >= arrival:
                        arrival = "Due"
                    else:
                        arrival = "In %s" % utils.to_pretty_time(
                            (arrival-now).total_seconds(), max_units=1,
                            minimum_unit=utils.UNIT_MINUTE)

                    destinations[destination] = "%s (%s)" % (
                        train["towards"], arrival)

            if destinations:
                event["stdout"].write("%s: %s" % (
                    station["name"], ", ".join(destinations.values())))
        else:
            event["stdout"].write("Unknown station '%s'" % query)
