import time, typing, uuid
from src import Database, EventManager, Logging, PollHook

T_CALLBACK = typing.Callable[["Timer"], None]

class Timer(object):
    def __init__(self, id: str, context: typing.Optional[str], name: str,
            delay: float, next_due: typing.Optional[float], kwargs: dict,
            callback: T_CALLBACK):
        self.id = id
        self.context = context
        self.name = name
        self.delay = delay
        if next_due:
            self.next_due = next_due
        else:
            self.set_next_due()
        self.kwargs = kwargs
        self.callback = callback
        self._done = False

    def set_next_due(self):
        self.next_due = time.time()+self.delay
    def due(self) -> bool:
        return not self.done() and self.time_left() <= 0
    def time_left(self) -> float:
        return self.next_due-time.time()

    def redo(self):
        self._done = False
        self.set_next_due()
    def finish(self):
        self._done = True
    def cancel(self):
        self.finish()
    def done(self) -> bool:
        return self._done

class Timers(PollHook.PollHook):
    def __init__(self, database: Database.Database,
            events: EventManager.Events,
            log: Logging.Log):
        self.database = database
        self.events = events
        self.log = log
        self.timers = [] # type: typing.List[Timer]
        self.context_timers = {} # type: typing.Dict[str, typing.List[Timer]]

    def new_context(self, context: str) -> "TimersContext":
        return TimersContext(self, context)

    def setup(self, timers: typing.List[typing.Tuple[str, dict]]):
        for name, timer in timers:
            id = name.split("timer-", 1)[1]
            self._add(None, timer["name"], timer["delay"], timer[
                "next-due"], id, False, timer["kwargs"])

    def _persist(self, timer: Timer):
        self.database.bot_settings.set("timer-%s" % timer.id, {
            "name": timer.name, "delay": timer.delay,
            "next-due": timer.next_due, "kwargs": timer.kwargs})
    def _remove(self, timer: Timer):
        if timer.context:
            self.context_timers[timer.context].remove(timer)
            if not self.context_timers[timer.context]:
                del self.context_timers[timer.context]
        else:
            self.timers.remove(timer)
        self.database.bot_settings.delete("timer-%s" % timer.id)

    def add(self, name: str, callback: T_CALLBACK, delay: float,
            next_due: float=None, **kwargs) -> Timer:
        return self._add(None, name, delay, next_due, None, False, kwargs,
            callback=callback)
    def add_persistent(self, name: str, delay: float, next_due: float=None,
            **kwargs) -> Timer:
        return self._add(None, name, delay, next_due, None, True, kwargs)
    def _add(self, context: typing.Optional[str], name: str, delay: float,
            next_due: typing.Optional[float], id: typing.Optional[str],
            persist: bool, kwargs: dict, callback: T_CALLBACK=None) -> Timer:
        id = id or str(uuid.uuid4())

        if not callback:
            callback = lambda timer: self.events.on("timer.%s" % name).call(
                timer=timer, **kwargs)

        timer = Timer(id, context, name, delay, next_due, kwargs,
            callback=callback)
        if persist:
            self._persist(timer)

        if context and not persist:
            if not context in self.context_timers:
                self.context_timers[context] = []
            self.context_timers[context].append(timer)
        else:
            self.timers.append(timer)
        return timer

    def next(self) -> typing.Optional[float]:
        times = list(filter(None,
            [timer.time_left() for timer in self.get_timers()]))
        if not times:
            return None
        return max(min(times), 0)

    def get_timers(self) -> typing.List[Timer]:
        return self.timers + sum(self.context_timers.values(), [])

    def find_all(self, name: str) -> typing.List[Timer]:
        name_lower = name.lower()
        timers = self.get_timers()
        found = [] # type: typing.List[Timer]
        for timer in timers:
            if timer.name.lower() == name_lower:
                found.append(timer)

        return found

    def call(self):
        for timer in self.get_timers():
            if timer.due():
                timer.finish()
                timer.callback(timer)
            if timer.done():
                self._remove(timer)

    def purge_context(self, context: str):
        if context in self.context_timers:
            del self.context_timers[context]

class TimersContext(object):
    def __init__(self, parent: Timers, context: str):
        self._parent = parent
        self.context = context
    def add(self, name: str, callback: T_CALLBACK, delay: float,
            next_due: float=None, **kwargs) -> Timer:
        return self._parent._add(self.context, name, delay, next_due, None,
            False, kwargs, callback=callback)
    def add_persistent(self, name: str, delay: float, next_due: float=None,
            **kwargs) -> Timer:
        return self._parent._add(None, name, delay, next_due, None, True,
            kwargs)
    def find_all(self, name: str) -> typing.List[Timer]:
        return self._parent.find_all(name)
