#--depends-on commands
#--depends-on location

import datetime, enum
import pytz
from src import ModuleManager, utils

NOLOCATION_USER = "%s doesn't have a location set"
NOLOCATION_NAME = "Unknown location '%s'"

class LocationType(enum.Enum):
    USER = 1
    NAME = 2

class Module(ModuleManager.BaseModule):
    _name = "Time"

    def _find_setting(self, event):
        query = None
        target_user = None

        if event["args"]:
            query = event["args"]
            if len(event["args_split"]) == 1 and event["server"].has_user_id(
                    event["args_split"][0]):
                target_user = event["server"].get_user(event["args_split"][0])
        else:
            target_user = event["user"]

        if target_user:
            location = target_user.get_setting("location", None)
            if location:
                return (LocationType.USER, target_user.nickname,
                    location["timezone"])

        if query:
            location = self.exports.get("get-location")(query)
            if location:
                return (LocationType.NAME, location["name"],
                    location["timezone"])
            else:
                return LocationType.NAME, event["args"], None

    def _timezoned(self, dt, timezone):
        dt = dt.astimezone(pytz.timezone(timezone))
        utc_offset = (dt.utcoffset().total_seconds()/60)/60
        tz = "UTC"
        if not utc_offset == 0.0:
            if utc_offset > 0:
                tz += "+"
            tz += "%g" % utc_offset
        return "%s %s" % (utils.datetime.format.datetime_human(dt), tz)

    @utils.hook("received.command.time")
    @utils.kwarg("help", "Get the time for you or someone else")
    @utils.kwarg("usage", "[nickname]")
    @utils.kwarg("require_setting", "location")
    @utils.kwarg("require_setting_unless", "1")
    def time(self, event):
        type, name, timezone = self._find_setting(event)

        if not timezone == None:
            human = self._timezoned(datetime.datetime.now(), timezone)

            out = None
            if type == LocationType.USER:
                out = "Time for %s: %s" % (name, human)
            else:
                out = "It is %s in %s" % (human, name)
            event["stdout"].write(out)
        else:
            out = None
            if type == LocationType.USER:
                out = NOLOCATION_USER
            else:
                out = NOLOCATION_NAME

            event["stderr"].write(out % name)

    @utils.export("time-localise")
    def time_localise(self, user, dt):
        location = user.get_setting("location", None)
        timezone = "UTC"
        if not location == None:
            timezone = location["timezone"]
        return self._timezoned(dt, timezone)
