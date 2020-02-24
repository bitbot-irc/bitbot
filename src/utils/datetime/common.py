import datetime as _datetime
import enum

ISO8601_FORMAT_DT = "%Y-%m-%dT%H:%M:%S"
ISO8601_FORMAT_TZ = "%z"

TIME_HUMAN = "%H:%M:%S"
DATE_HUMAN = "%Y-%m-%d"

class TimeSpec(enum.Enum):
    NORMAL = 1
    MILLISECOND = 2

TIME_SECOND = 1
TIME_MINUTE = TIME_SECOND*60
TIME_HOUR = TIME_MINUTE*60
TIME_DAY = TIME_HOUR*24
TIME_WEEK = TIME_DAY*7

SECONDS_MINUTES = 60
SECONDS_HOURS = SECONDS_MINUTES*60
SECONDS_DAYS = SECONDS_HOURS*24
SECONDS_WEEKS = SECONDS_DAYS*7

UNIT_MINIMUM = 6
UNIT_SECOND = 5
UNIT_MINUTE = 4
UNIT_HOUR = 3
UNIT_DAY = 2
UNIT_WEEK = 1
UNIT_MONTH = 1
UNIT_YEAR = 1

def utcnow() -> _datetime.datetime:
    return _datetime.datetime.utcnow().replace(tzinfo=_datetime.timezone.utc)

def timestamp(seconds: float) -> _datetime.datetime:
    return _datetime.datetime.fromtimestamp(seconds).replace(
        tzinfo=_datetime.timezone.utc)

def seconds_since(dt: _datetime.datetime) -> float:
    return (utcnow()-dt).total_seconds()

class RelativeDirection(enum.Enum):
    FORWARD = 1
    BACKWARD = 2
