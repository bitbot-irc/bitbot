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
        target_user = event["user"]

        if event["args"]:
            if len(event["args_split"]) == 1 and event["server"].has_user_id(
                    event["args_split"][0]):
                target_user = event["server"].get_user(event["args_split"][0])
            else:
                location = self.exports.get_one("get-location")(event["args"])
                if location:
                    return (LocationType.NAME, location["name"],
                        location["timezone"])
                else:
                    return LocationType.NAME, event["args"], None

        if target_user:
            location = target_user.get_setting("location", None)
            if location:
                return (LocationType.USER, target_user.nickname,
                    location["timezone"])
            else:
                return LocationType.USER, target_user.nickname, None


    @utils.hook("received.command.time")
    @utils.kwarg("help", "Get the time for you or someone else")
    @utils.kwarg("usage", "[nickname]")
    @utils.kwarg("require_setting", "location")
    @utils.kwarg("require_setting_unless", "1")
    def time(self, event):
        type, name, timezone = self._find_setting(event)

        if not timezone == None:
            dt = datetime.datetime.now(tz=pytz.timezone(timezone))
            human = utils.datetime_human(dt)

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

    @utils.hook("received.command.timezone")
    @utils.kwarg("help", "Get the timezone for you or someone else")
    @utils.kwarg("usage", "[nickname]")
    @utils.kwarg("require_setting", "location")
    @utils.kwarg("require_setting_unless", "1")
    def timezone(self, event):
        type, name, timezone = self._find_setting(event)
        if not timezone == None:
            event["stdout"].write("%s is in %s" % (name, timezone))
        else:
            out = None
            if type == LocationType.USER:
                out = NOLOCATION_USER
            else:
                out = NOLOCATION_NAME
            event["stderr"].write(out % name)
