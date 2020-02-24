import contextlib, enum, ipaddress, multiprocessing, os.path, queue, signal
import threading, typing
from . import cli, consts, datetime, decorators, io, irc, http, parse, security

from .decorators import export, hook, kwarg, spec
from .settings import (BoolSetting, FunctionSetting, IntRangeSetting,
    IntSetting, OptionsSetting, sensitive_format, SensitiveSetting, Setting)
from .errors import (EventError, EventNotEnoughArgsError, EventResultsError,
    EventUsageError)

class Direction(enum.Enum):
    Send = 0
    Recv = 1

def prevent_highlight(nickname: str) -> str:
    return nickname[0]+"\u200c"+nickname[1:]

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
    def __contains__(self, key: typing.Any) -> bool:
        if isinstance(key, str):
            return dict.__contains__(self, key.lower())
        else:
            raise TypeError("Expected string, not %r" % key)
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

DeadlineProcessReturnType = typing.TypeVar("DeadlineProcessReturnType")
def deadline_process(func: typing.Callable[[], DeadlineProcessReturnType],
        seconds: int=10) -> DeadlineProcessReturnType:
    q: multiprocessing.Queue[
        typing.Tuple[bool, DeadlineProcessReturnType]] = multiprocessing.Queue()
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
        p.kill() # type: ignore  # to make mypy pass on Python 3.6
        deadlined = True
    finally:
        q.close()

    if deadlined:
        _raise_deadline()

    if success:
        return out
    else:
        raise out # type: ignore

def git_commit(bot_directory: str
        ) -> typing.Tuple[typing.Optional[str], typing.Optional[str]]:
    git_dir = os.path.join(bot_directory, ".git")
    head_filepath = os.path.join(git_dir, "HEAD")
    if os.path.isfile(head_filepath):
        with open(head_filepath, "r") as head_file:
            ref_line = head_file.readline().strip()
            if not ref_line.startswith("ref: "):
                return None, ref_line
            else:
                ref = ref_line.split(" ", 1)[1]
                branch = ref.rsplit("/", 1)[1]

                ref_filepath = os.path.join(git_dir, ref)
                with open(ref_filepath, "r") as ref_file:
                    return branch, ref_file.readline().strip()[:8]
    return None, None
