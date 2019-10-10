import contextlib, datetime, decimal, enum, io, ipaddress, multiprocessing
import queue, re, signal, threading, typing
from src.utils import cli, consts, irc, http, parse, security

class Direction(enum.Enum):
    Send = 0
    Recv = 1

ISO8601_PARSE = "%Y-%m-%dT%H:%M:%S%z"
ISO8601_PARSE_MICROSECONDS = "%Y-%m-%dT%H:%M:%S.%f%z"

ISO8601_FORMAT_DT = "%Y-%m-%dT%H:%M:%S"
ISO8601_FORMAT_TZ = "%z"


DATETIME_HUMAN = "%Y/%m/%d %H:%M:%S"

def datetime_utcnow() -> datetime.datetime:
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

def iso8601_format(dt: datetime.datetime, milliseconds: bool=False) -> str:
    dt_format = dt.strftime(ISO8601_FORMAT_DT)
    tz_format = dt.strftime(ISO8601_FORMAT_TZ)

    ms_format = ""
    if milliseconds:
        ms_format = ".%s" % str(int(dt.microsecond/1000)).zfill(3)

    return "%s%s%s" % (dt_format, ms_format, tz_format)
def iso8601_format_now(milliseconds: bool=False) -> str:
    return iso8601_format(datetime_utcnow(), milliseconds=milliseconds)
def iso8601_parse(s: str, microseconds: bool=False) -> datetime.datetime:
    fmt = ISO8601_PARSE_MICROSECONDS if microseconds else ISO8601_PARSE
    return datetime.datetime.strptime(s, fmt)

def datetime_human(dt: datetime.datetime):
    return datetime.datetime.strftime(dt, DATETIME_HUMAN)

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

class BitBotMagic(object):
    def __init__(self):
        self._hooks: typing.List[typing.Tuple[str, dict]] = []
        self._kwargs: typing.List[typing.Tuple[str, typing.Any]] = []
        self._exports: typing.List[typing.Tuple[str, typing.Any]] = []
    def add_hook(self, hook: str, kwargs: dict):
        self._hooks.append((hook, kwargs))
    def add_kwarg(self, key: str, value: typing.Any):
        self._kwargs.append((key, value))

    def get_hooks(self):
        hooks: typing.List[typing.Tuple[str, typing.List[str, typing.Any]]] = []
        for hook, kwargs in self._hooks:
            hooks.append((hook, self._kwargs.copy()+list(kwargs.items())))
        return hooks

    def add_export(self, key: str, value: typing.Any):
        self._exports.append((key, value))
    def get_exports(self):
        return self._exports.copy()

def get_magic(obj: typing.Any):
    if not has_magic(obj):
        setattr(obj, consts.BITBOT_MAGIC, BitBotMagic())
    return getattr(obj, consts.BITBOT_MAGIC)
def has_magic(obj: typing.Any):
    return hasattr(obj, consts.BITBOT_MAGIC)

def hook(event: str, **kwargs):
    def _hook_func(func):
        magic = get_magic(func)
        magic.add_hook(event, kwargs)
        return func
    return _hook_func
def export(setting: str, value: typing.Any):
    def _export_func(module):
        magic = get_magic(module)
        magic.add_export(setting, value)
        return module
    return _export_func
def kwarg(key: str, value: typing.Any):
    def _kwarg_func(func):
        magic = get_magic(func)
        magic.add_kwarg(key, value)
        return func
    return _kwarg_func

class MultiCheck(object):
    def __init__(self,
            requests: typing.List[typing.Tuple[str, typing.List[str]]]):
        self._requests = requests
    def to_multi(self):
        return self
    def requests(self):
        return self._requests[:]
    def __or__(self, other: "Check"):
        return MultiCheck(self._requests+[(other.request, other.args)])
class Check(object):
    def __init__(self, request: str, *args: str):
        self.request = request
        self.args = list(args)
    def to_multi(self):
        return MultiCheck([(self.request, self.args)])
    def __or__(self, other: "Check"):
        return MultiCheck([(self.request, self.args),
            (other.request, other.args)])

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
    def __contains__(self, key: str):
        return dict.__contains__(self, key.lower())
    def get(self, key: str, default: typing.Any=None):
        return dict.get(self, key.lower(), default)

def is_ip(s: str) -> bool:
    try:
        ipaddress.ip_address(s)
    except ValueError:
        return False
    return True

def is_main_thread() -> bool:
    return threading.current_thread() is threading.main_thread()

class SettingParseException(Exception):
    pass

class Setting(object):
    example: typing.Optional[str] = None
    def __init__(self, name: str, help: str=None, example: str=None):
        self.name = name
        self.help = help
        if not example == None:
            self.example = example
    def parse(self, value: str) -> typing.Any:
        return value

    def get_example(self):
        if not self.example == None:
            return "Example: %s" % self.example
        else:
            return self._format_example()
    def _format_example(self):
        return None

    def format(self, value: typing.Any):
        return repr(value)

SETTING_TRUE = ["true", "yes", "on", "y"]
SETTING_FALSE = ["false", "no", "off", "n"]
class BoolSetting(Setting):
    example = "on"
    def parse(self, value: str) -> typing.Any:
        value_lower = value.lower()
        if value_lower in SETTING_TRUE:
            return True
        elif value_lower in SETTING_FALSE:
            return False
        return None

class IntSetting(Setting):
    example = "10"
    def parse(self, value: str) -> typing.Any:
        if value == "0":
            return 0
        else:
            stripped = value.lstrip("0")
            if stripped.isdigit():
                return int(stripped)
        return None

class IntRangeSetting(IntSetting):
    example = None
    def __init__(self, n_min: int, n_max: int, name: str, help: str=None,
            example: str=None):
        self._n_min = n_min
        self._n_max = n_max
        Setting.__init__(self, name, help, example)

    def parse(self, value: str) -> typing.Any:
        out = IntSetting.parse(self, value)
        if not out == None and self._n_min <= out <= self._n_max:
            return out
        return None

    def _format_example(self):
        return "Must be between %d and %d" % (self._n_min, self._n_max)

class OptionsSetting(Setting):
    def __init__(self, options: typing.List[str], name: str, help: str=None,
            example: str=None,
            options_factory: typing.Callable[[], typing.List[str]]=None):
        self._options = options
        self._options_factory = options_factory
        Setting.__init__(self, name, help, example)

    def _get_options(self):
        if not self._options_factory == None:
            return self._options_factory()
        else:
            return self._options

    def parse(self, value: str) -> typing.Any:
        value_lower = value.lower()
        for option in self._get_options():
            if option.lower() == value_lower:
                return option
        return None

    def _format_example(self):
        options = self._get_options()
        options_str = ["'%s'" % option for option in options]
        return "Options: %s" % ", ".join(options_str)

class FunctionSetting(Setting):
    def __init__(self, func: typing.Callable[[str], bool], name: str,
            help: str=None, example: str=None, format=None):
        self._func = func
        Setting.__init__(self, name, help, example)
        if not format == None:
            self.format = format

    def parse(self, value: str) -> typing.Any:
        return self._func(value)

def sensitive_format(value: typing.Any):
    return "*"*16

class SensitiveSetting(Setting):
    def format(self, value: typing.Any):
        return sensitive_format(value)

class DeadlineExceededException(Exception):
    pass
def _raise_deadline():
    raise DeadlineExceededException()

@contextlib.contextmanager
def deadline(seconds: int=10):
    old_handler = signal.signal(signal.SIGALRM,
        lambda _1, _2: _raise_deadline())
    old_seconds, _ = signal.setitimer(signal.ITIMER_REAL, seconds, 0)

    try:
        if not old_seconds == 0.0 and seconds > old_seconds:
            raise ValueError(
                "Deadline timeout larger than parent deadline (%s > %s)" %
                (seconds, old_seconds))

        yield
    finally:
        signal.signal(signal.SIGALRM, old_handler)
        signal.setitimer(signal.ITIMER_REAL, old_seconds, 0)

def deadline_process(func: typing.Callable[[], None], seconds: int=10):
    q = multiprocessing.Queue()
    def _wrap(func, q):
        try:
            q.put([True, func()])
        except Exception as e:
            q.put([False, e])

    p = multiprocessing.Process(target=_wrap, args=(func, q))
    p.start()

    deadlined = False
    try:
        success, out = q.get(block=True, timeout=seconds)
    except queue.Empty:
        p.kill()
        deadlined = True
    finally:
        q.close()

    if deadlined:
        _raise_deadline()

    if success:
        return out
    else:
        raise out
