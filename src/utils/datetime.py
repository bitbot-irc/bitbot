import enum, re, typing
import datetime as _datetime
import dateutil.parser

ISO8601_FORMAT_DT = "%Y-%m-%dT%H:%M:%S"
ISO8601_FORMAT_TZ = "%z"

TIME_HUMAN = "%H:%M:%S"
DATE_HUMAN = "%Y-%m-%d"

class TimeSpec(enum.Enum):
    NORMAL = 1
    MILLISECOND = 2

def utcnow() -> _datetime.datetime:
    return _datetime.datetime.utcnow().replace(tzinfo=_datetime.timezone.utc)
def datetime_timestamp(seconds: float) -> _datetime.datetime:
    return _datetime.datetime.fromtimestamp(seconds).replace(
        tzinfo=_datetime.timezone.utc)

def iso8601_format(dt: _datetime.datetime, timespec: TimeSpec=TimeSpec.NORMAL
        ) -> str:
    dt_format = dt.strftime(ISO8601_FORMAT_DT)
    tz_format = dt.strftime(ISO8601_FORMAT_TZ)

    ms_format = ""
    if timespec == TimeSpec.MILLISECOND:
        ms_format = ".%s" % str(int(dt.microsecond/1000)).zfill(3)

    return "%s%s%s" % (dt_format, ms_format, tz_format)
def iso8601_format_now(timespec: TimeSpec=TimeSpec.NORMAL) -> str:
    return iso8601_format(utcnow(), timespec)

def iso8601_parse(s: str) -> _datetime.datetime:
    return dateutil.parser.parse(s)

def datetime_human(dt: _datetime.datetime, timespec: TimeSpec=TimeSpec.NORMAL):
    date = _datetime.datetime.strftime(dt, DATE_HUMAN)
    time = _datetime.datetime.strftime(dt, TIME_HUMAN)
    if timespec == TimeSpec.MILLISECOND:
        time += ".%s" % str(int(dt.microsecond/1000)).zfill(3)
    return "%s %s" % (date, time)
def date_human(dt: _datetime.datetime, timespec: TimeSpec=TimeSpec.NORMAL):
    return _datetime.datetime.strftime(dt, DATE_HUMAN)

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

REGEX_PRETTYTIME = re.compile(
    r"(?:(\d+)w)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", re.I)

SECONDS_MINUTES = 60
SECONDS_HOURS = SECONDS_MINUTES*60
SECONDS_DAYS = SECONDS_HOURS*24
SECONDS_WEEKS = SECONDS_DAYS*7

def from_pretty_time(pretty_time: str) -> typing.Optional[int]:
    seconds = 0

    match = re.match(REGEX_PRETTYTIME, pretty_time)
    if match:
        seconds += int(match.group(1) or 0)*SECONDS_WEEKS
        seconds += int(match.group(2) or 0)*SECONDS_DAYS
        seconds += int(match.group(3) or 0)*SECONDS_HOURS
        seconds += int(match.group(4) or 0)*SECONDS_MINUTES
        seconds += int(match.group(5) or 0)

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
    out = []

    units = 0
    if weeks and minimum_unit >= UNIT_WEEK and units < max_units:
        out.append("%dw" % weeks)
        units += 1
    if days and minimum_unit >= UNIT_DAY and units < max_units:
        out.append("%dd" % days)
        units += 1
    if hours and minimum_unit >= UNIT_HOUR and units < max_units:
        out.append("%dh" % hours)
        units += 1
    if minutes and minimum_unit >= UNIT_MINUTE and units < max_units:
        out.append("%dm" % minutes)
        units += 1
    if seconds and minimum_unit >= UNIT_SECOND and units < max_units:
        out.append("%ds" % seconds)
        units += 1
    return " ".join(out)

