import datetime, decimal, enum, io, ipaddress, re, typing
from src.utils import cli, consts, irc, http, parse, security

class Direction(enum.Enum):
    SEND = 0
    RECV = 1

ISO8601_PARSE = "%Y-%m-%dT%H:%M:%S%z"

def iso8601_format(dt: datetime.datetime) -> str:
    formatted = dt.isoformat(timespec="milliseconds")
    return "%sZ" % formatted

TIME_SECOND = 1
TIME_MINUTE = TIME_SECOND*60
TIME_HOUR = TIME_MINUTE*60
TIME_DAY = TIME_HOUR*24
TIME_WEEK = TIME_DAY*7

def time_unit(seconds: int) -> typing.Tuple[int, str]:
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
    return (since, unit)

REGEX_PRETTYTIME = re.compile("\d+[wdhms]", re.I)

SECONDS_MINUTES = 60
SECONDS_HOURS = SECONDS_MINUTES*60
SECONDS_DAYS = SECONDS_HOURS*24
SECONDS_WEEKS = SECONDS_DAYS*7

def from_pretty_time(pretty_time: str) -> typing.Optional[int]:
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
    return None

UNIT_MINIMUM = 6
UNIT_SECOND = 5
UNIT_MINUTE = 4
UNIT_HOUR = 3
UNIT_DAY = 2
UNIT_WEEK = 1
def to_pretty_time(total_seconds: int, minimum_unit: int=UNIT_SECOND,
        max_units: int=UNIT_MINIMUM) -> str:
    if total_seconds == 0:
        return "0s"

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

def parse_number(s: str) -> str:
    try:
        decimal.Decimal(s)
        return s
    except:
        pass

    unit = s[-1].lower()
    number_str = s[:-1]
    try:
        number = decimal.Decimal(number_str)
    except:
        raise ValueError("Invalid format '%s' passed to parse_number" %
            number_str)

    if unit == "k":
        number *= decimal.Decimal("1_000")
    elif unit == "m":
        number *= decimal.Decimal("1_000_000")
    elif unit == "b":
        number *= decimal.Decimal("1_000_000_000")
    else:
        raise ValueError("Unknown unit '%s' given to parse_number" % unit)
    return str(number)

IS_TRUE = ["true", "yes", "on", "y"]
IS_FALSE = ["false", "no", "off", "n"]
def bool_or_none(s: str) -> typing.Optional[bool]:
    s = s.lower()
    if s in IS_TRUE:
        return True
    elif s in IS_FALSE:
        return False
    return None
def int_or_none(s: str) -> typing.Optional[int]:
    stripped_s = s.lstrip("0")
    if stripped_s.isdigit():
        return int(stripped_s)
    return None

def prevent_highlight(nickname: str) -> str:
    return nickname[0]+"\u200c"+nickname[1:]

class EventError(Exception):
    pass
class EventsResultsError(EventError):
    def __init__(self):
        EventError.__init__(self, "Failed to load results")
class EventsNotEnoughArgsError(EventError):
    def __init__(self, n):
        EventError.__init__(self, "Not enough arguments (minimum %d)" % n)
class EventsUsageError(EventError):
    def __init__(self, usage):
        EventError.__init__(self, "Not enough arguments, usage: %s" % usage)

def _set_get_append(obj: typing.Any, setting: str, item: typing.Any):
    if not hasattr(obj, setting):
        setattr(obj, setting, [])
    getattr(obj, setting).append(item)
def hook(event: str, **kwargs):
    def _hook_func(func):
        _set_get_append(func, consts.BITBOT_HOOKS_MAGIC,
            {"event": event, "kwargs": kwargs})
        return func
    return _hook_func
def export(setting: str, value: typing.Any):
    def _export_func(module):
        _set_get_append(module, consts.BITBOT_EXPORTS_MAGIC,
            {"setting": setting, "value": value})
        return module
    return _export_func

TOP_10_CALLABLE = typing.Callable[[typing.Any], typing.Any]
def top_10(items: typing.Dict[typing.Any, typing.Any],
        convert_key: TOP_10_CALLABLE=lambda x: x,
        value_format: TOP_10_CALLABLE=lambda x: x):
    top_10 = sorted(items.keys())
    top_10 = sorted(top_10, key=items.get, reverse=True)[:10]

    top_10_items = []
    for key in top_10:
        top_10_items.append("%s (%s)" % (convert_key(key),
            value_format(items[key])))

    return top_10_items

class CaseInsensitiveDict(dict):
    def __init__(self, other: typing.Dict[str, typing.Any]):
        dict.__init__(self, ((k.lower(), v) for k, v in other.items()))
    def __getitem__(self, key: str) -> typing.Any:
        return dict.__getitem__(self, key.lower())
    def __setitem__(self, key: str, value: typing.Any) -> typing.Any:
        return dict.__setitem__(self, key.lower(), value)

def is_ip(s: str) -> bool:
    try:
        ipaddress.ip_address(s)
    except ValueError:
        return False
    return True

def encode_truncate(s: str, encoding: str, byte_max: int
        ) -> typing.Tuple[bytes, str]:
    encoded = b""
    truncated = ""
    for i, character in enumerate(s):
        encoded_character = character.encode(encoding)
        if len(encoded + encoded_character) > byte_max:
            truncated = s[i:]
            break
        else:
            encoded += encoded_character
    return encoded, truncated
