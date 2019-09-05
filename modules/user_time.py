#--depends-on commands
#--depends-on location

import datetime
import pytz
from src import ModuleManager, utils

NOLOCATION = "%s doesn't have a location set"

class Module(ModuleManager.BaseModule):
    _name = "Time"

    def _find_setting(self, event):
        target_user = event["user"]

        if event["args"]:
            target_user = event["server"].get_user(event["args_split"][0])

        return target_user, target_user.get_setting("location", None)

    @utils.hook("received.command.time")
    @utils.kwarg("help", "Get the time for you or someone else")
    @utils.kwarg("usage", "[nickname]")
    @utils.kwarg("require_setting", "location")
    @utils.kwarg("require_setting_unless", "1")
    def time(self, event):
        target_user, location = self._find_setting(event)
        if not location == None:
            dt = datetime.datetime.now(tz=pytz.timezone(location["timezone"]))
            human = utils.datetime_human(dt)
            event["stdout"].write("Time for %s: %s" % (target_user.nickname,
                human))
        else:
            event["stderr"].write(NOLOCATION % target_user.nickname)

    @utils.hook("received.command.timezone")
    @utils.kwarg("help", "Get the timezone for you or someone else")
    @utils.kwarg("usage", "[nickname]")
    @utils.kwarg("require_setting", "location")
    @utils.kwarg("require_setting_unless", "1")
    def timezone(self, event):
        target_user, location = self._find_setting(event)
        if not location == None:
            event["stdout"].write("%s is in %s" % (target_user.nickname,
                location["timezone"]))
        else:
            event["stderr"].write(NOLOCATION % target_user.nickname)
