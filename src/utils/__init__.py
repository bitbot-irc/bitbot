from . import irc, http

import io, re
from src import ModuleManager

TIME_SECOND = 1
TIME_MINUTE = TIME_SECOND*60
TIME_HOUR = TIME_MINUTE*60
TIME_DAY = TIME_HOUR*24
TIME_WEEK = TIME_DAY*7

def time_unit(seconds):
    since = None
    unit = None
    if seconds >= TIME_WEEK:
        since = seconds/TIME_WEEK
        unit = "week"
    elif seconds >= TIME_DAY:
        since = seconds/TIME_DAY
        unit = "day"
    elif seconds >= TIME_HOUR:
        since = seconds/TIME_HOUR
        unit = "hour"
    elif seconds >= TIME_MINUTE:
        since = seconds/TIME_MINUTE
        unit = "minute"
    else:
        since = seconds
        unit = "second"
    since = int(since)
    if since > 1:
        unit = "%ss" % unit # pluralise the unit
    return [since, unit]

REGEX_PRETTYTIME = re.compile("\d+[wdhms]", re.I)

SECONDS_MINUTES = 60
SECONDS_HOURS = SECONDS_MINUTES*60
SECONDS_DAYS = SECONDS_HOURS*24
SECONDS_WEEKS = SECONDS_DAYS*7

def from_pretty_time(pretty_time):
    seconds = 0
    for match in re.findall(REGEX_PRETTYTIME, pretty_time):
        number, unit = int(match[:-1]), match[-1].lower()
        if unit == "m":
            number = number*SECONDS_MINUTES
        elif unit == "h":
            number = number*SECONDS_HOURS
        elif unit == "d":
            number = number*SECONDS_DAYS
        elif unit == "w":
            number = number*SECONDS_WEEKS
        seconds += number
    if seconds > 0:
        return seconds

UNIT_SECOND = 5
UNIT_MINUTE = 4
UNIT_HOUR = 3
UNIT_DAY = 2
UNIT_WEEK = 1
def to_pretty_time(total_seconds, minimum_unit=UNIT_SECOND, max_units=6):
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)
    out = ""

    units = 0
    if weeks and minimum_unit >= UNIT_WEEK and units < max_units:
        out += "%dw" % weeks
        units += 1
    if days and minimum_unit >= UNIT_DAY and units < max_units:
        out += "%dd" % days
        units += 1
    if hours and minimum_unit >= UNIT_HOUR and units < max_units:
        out += "%dh" % hours
        units += 1
    if minutes and minimum_unit >= UNIT_MINUTE and units < max_units:
        out += "%dm" % minutes
        units += 1
    if seconds and minimum_unit >= UNIT_SECOND and units < max_units:
        out += "%ds" % seconds
        units += 1
    return out

IS_TRUE = ["true", "yes", "on", "y"]
IS_FALSE = ["false", "no", "off", "n"]
def bool_or_none(s):
    s = s.lower()
    if s in IS_TRUE:
        return True
    elif s in IS_FALSE:
        return False
def int_or_none(s):
    stripped_s = s.lstrip("0")
    if stripped_s.isdigit():
        return int(stripped_s)

def get_closest_setting(event, setting, default=None):
    server = event["server"]
    if "channel" in event:
        closest = event["channel"]
    elif "target" in event and "is_channel" in event and event["is_channel"]:
        closest = event["target"]
    else:
        closest = event["user"]
    return closest.get_setting(setting, server.get_setting(setting, default))

def prevent_highlight(nickname):
    return nickname[0]+"\u200c"+nickname[1:]

def _set_get_append(obj, setting, item):
    if not hasattr(obj, setting):
        setattr(obj, setting, [])
    getattr(obj, setting).append(item)
def hook(event, **kwargs):
    def _hook_func(func):
        _set_get_append(func, ModuleManager.BITBOT_HOOKS_MAGIC,
            {"event": event, "kwargs": kwargs})
        return func
    return _hook_func
def export(setting, value):
    def _export_func(module):
        _set_get_append(module, ModuleManager.BITBOT_EXPORTS_MAGIC,
            {"setting": setting, "value": value})
        return module
    return _export_func

def get_hashflags(filename):
    hashflags = {}
    with io.open(filename, mode="r", encoding="utf8") as f:
        for line in f:
            line = line.strip("\n")
            if not line.startswith("#"):
                break
            elif line.startswith("#--"):
                line_split = line.split(" ", 1)
                hashflag = line_split[0][3:]
                value = None

                if len(line_split) > 1:
                    value = line_split[1]
                hashflags[hashflag] = value
    return hashflags.items()

class Docstring(object):
    def __init__(self, description, items):
        self.description = description
        self.items = items

def parse_docstring(s):
    description = ""
    last_item = None
    items = {}
    if s:
        for line in s.split("\n"):
            line = line.strip()

            if line:
                if line[0] == ":":
                    key, _, value = line[1:].partition(": ")
                    last_item = key
                    items[key] = value
                else:
                    if last_item:
                        items[last_item] += " %s" % line
                    else:
                        if description:
                            description += " "
                        description += line
    return Docstring(description, items)

def top_10(items, convert_key=lambda x: x, value_format=lambda x: x):
        top_10 = sorted(items.keys())
        top_10 = sorted(top_10, key=items.get, reverse=True)[:10]

        top_10_items = []
        for key in top_10:
            top_10_items.append("%s (%s)" % (convert_key(key),
                value_format(items[key])))

        return top_10_items
