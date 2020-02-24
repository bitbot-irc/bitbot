import typing
import datetime as _datetime
import dateutil.relativedelta
from .common import *

def iso8601(dt: _datetime.datetime, timespec: TimeSpec=TimeSpec.NORMAL
        ) -> str:
    dt_format = dt.strftime(ISO8601_FORMAT_DT)
    tz_format = dt.strftime(ISO8601_FORMAT_TZ)

    ms_format = ""
    if timespec == TimeSpec.MILLISECOND:
        ms_format = ".%s" % str(int(dt.microsecond/1000)).zfill(3)

    return "%s%s%s" % (dt_format, ms_format, tz_format)
def iso8601_now(timespec: TimeSpec=TimeSpec.NORMAL) -> str:
    return iso8601(utcnow(), timespec)

def datetime_human(dt: _datetime.datetime, timespec: TimeSpec=TimeSpec.NORMAL):
    date = _datetime.datetime.strftime(dt, DATE_HUMAN)
    time = _datetime.datetime.strftime(dt, TIME_HUMAN)
    if timespec == TimeSpec.MILLISECOND:
        time += ".%s" % str(int(dt.microsecond/1000)).zfill(3)
    return "%s %s" % (date, time)
def date_human(dt: _datetime.datetime, timespec: TimeSpec=TimeSpec.NORMAL):
    return _datetime.datetime.strftime(dt, DATE_HUMAN)

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

def to_pretty_time(total_seconds: int, max_units: int=UNIT_MINIMUM,
        direction: typing.Optional[RelativeDirection]=None) -> str:
    if total_seconds == 0:
        return "0s"

    if not direction == None:
        now = utcnow()
        later = now
        mod = _datetime.timedelta(seconds=total_seconds)
        if direction == RelativeDirection.FORWARD:
            later += mod
        else:
            later -= mod

        dts = [later, now]
        relative = dateutil.relativedelta.relativedelta(max(dts), min(dts))
        years = relative.years
        months = relative.months
        weeks, days = divmod(relative.days, 7)
        hours = relative.hours
        minutes = relative.minutes
        seconds = relative.seconds
    else:
        years, months    = 0, 0
        weeks, days      = divmod(total_seconds, SECONDS_WEEKS)
        days, hours      = divmod(days, SECONDS_DAYS)
        hours, minutes   = divmod(hours, SECONDS_HOURS)
        minutes, seconds = divmod(minutes, SECONDS_MINUTES)

    out: typing.List[str] = []
    if years and len(out) < max_units:
        out.append("%dy" % years)
    if months and len(out) < max_units:
        out.append("%dmo" % months)
    if weeks and len(out) < max_units:
        out.append("%dw" % weeks)
    if days and len(out) < max_units:
        out.append("%dd" % days)
    if hours and len(out) < max_units:
        out.append("%dh" % hours)
    if minutes and len(out) < max_units:
        out.append("%dmi" % minutes)
    if seconds and len(out) < max_units:
        out.append("%ds" % seconds)

    return " ".join(out)

def to_pretty_since(total_seconds: int, max_units: int=UNIT_MINIMUM
        ) -> str:
    return to_pretty_time(total_seconds, max_units, RelativeDirection.BACKWARD)
def to_pretty_until(total_seconds: int, max_units: int=UNIT_MINIMUM
        ) -> str:
    return to_pretty_time(total_seconds, max_units, RelativeDirection.FORWARD)
