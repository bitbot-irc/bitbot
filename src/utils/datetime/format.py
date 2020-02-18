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

def to_pretty_time(total_seconds: int, minimum_unit: int=UNIT_SECOND,
        max_units: int=UNIT_MINIMUM) -> str:
    if total_seconds == 0:
        return "0s"

    now = utcnow()
    later = now+_datetime.timedelta(seconds=total_seconds)
    relative = dateutil.relativedelta.relativedelta(later, now)

    out: typing.List[str] = []
    if relative.years and minimum_unit >= UNIT_YEAR and len(out) < max_units:
        out.append("%dy" % relative.years)
    if relative.months and minimum_unit >= UNIT_MONTH and len(out) < max_units:
        out.append("%dmo" % relative.months)
    weeks, days = divmod(relative.days, 7)
    if weeks and minimum_unit >= UNIT_WEEK and len(out) < max_units:
        out.append("%dw" % weeks)
    if days and minimum_unit >= UNIT_DAY and len(out) < max_units:
        out.append("%dd" % days)
    if relative.hours and minimum_unit >= UNIT_HOUR and len(out) < max_units:
        out.append("%dh" % relative.hours)
    if relative.minutes and minimum_unit >= UNIT_MINUTE and len(out) < max_units:
        out.append("%dmi" % relative.minutes)
    if relative.seconds and minimum_unit >= UNIT_SECOND and len(out) < max_units:
        out.append("%ds" % relative.seconds)

    return " ".join(out)

