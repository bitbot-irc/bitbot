from src import ModuleManager, utils
import pytz

_lower_timezones = {}
for tz in pytz.all_timezones:
    if "/" in tz:
        _lower_timezones[tz.split("/", 1)[1].lower()] = tz
    _lower_timezones[tz.lower()] = tz

def _find_tz(s):
    return _lower_timezones.get(s.lower(), None)

@utils.export("set", {"setting": "location", "help": "Set your location",
    "validate": _find_tz})
class Module(ModuleManager.BaseModule):
    pass
