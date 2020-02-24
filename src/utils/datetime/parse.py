import re, typing
import datetime as _datetime
import dateutil.parser, isodate
from .common import *

def iso8601(s: str) -> _datetime.datetime:
    return dateutil.parser.parse(s)
def iso8601_duration(s: str) -> _datetime.timedelta:
    return isodate.parse_duration(s)

def date_human(s: str) -> typing.Optional[_datetime.datetime]:
    try:
        return _datetime.datetime.strptime(s, DATE_HUMAN)
    except ValueError:
        return None

REGEX_PRETTYTIME = re.compile(
    r"(?:(\d+)w)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", re.I)

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
