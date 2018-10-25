import time, uuid

class Timer(object):
    def __init__(self, id, context, name, delay, next_due, kwargs):
        self.id = id
        self.context = context
        self.name = name
        self.delay = delay
        if next_due:
            self.next_due = next_due
        else:
            self.set_next_due()
        self.kwargs = kwargs
        self._done = False

    def set_next_due(self):
        self.next_due = time.time()+self.delay
    def due(self):
        return self.time_left() <= 0
    def time_left(self):
        return self.next_due-time.time()

    def redo(self):
        self._done = False
        self.set_next_due()
    def finish(self):
        self._done = True
    def done(self):
        return self._done

class TimersContext(object):
    def __init__(self, parent, context):
        self._parent = parent
        self.context = context
    def add(self, name, delay, next_due=None, **kwargs):
        self._parent._add(self.context, name, delay, next_due, None, False,
            kwargs)
    def add_persistent(self, name, delay, next_due=None, **kwargs):
        self._parent._add(None, name, delay, next_due, None, True,
            kwargs)

class Timers(object):
    def __init__(self, database, events, log):
        self.database = database
        self.events = events
        self.log = log
        self.timers = []
        self.context_timers = {}

    def new_context(self, context):
        return TimersContext(self, context)

    def setup(self, timers):
        for name, timer in timers:
            id = name.split("timer-", 1)[1]
            self._add(timer["name"], None, timer["delay"], timer[
                "next-due"], id, False, timer["kwargs"])

    def _persist(self, timer):
        self.database.bot_settings.set("timer-%s" % timer.id, {
            "name": timer.name, "delay": timer.delay,
            "next-due": timer.next_due, "kwargs": timer.kwargs})
    def _remove(self, timer):
        if timer.context:
            self.context_timers[timer.context].remove(timer)
            if not self.context_timers[timer.context]:
                del self.context_timers[timer.context]
        else:
            self.timers.remove(timer)
        self.database.bot_settings.delete("timer-%s" % timer.id)

    def add(self, name, delay, next_due=None, **kwargs):
        self._add(None, name, delay, next_due, None, False, kwargs)
    def add_persistent(self, name, delay, next_due=None, **kwargs):
        self._add(None, name, delay, next_due, None, True, kwargs)
    def _add(self, context, name, delay, next_due, id, persist, kwargs):
        id = id or uuid.uuid4().hex
        timer = Timer(id, context, name, delay, next_due, kwargs)
        if persist:
            self._persist(timer)

        if context and not persist:
            if not context in self.context_timers:
                self.context_timers[context] = []
            self.context_timers[context].append(timer)
        else:
            self.timers.append(timer)

    def next(self):
        times = filter(None, [timer.time_left() for timer in self.get_timers()])
        if not times:
            return None
        return max(min(times), 0)

    def get_timers(self):
        return self.timers + sum(self.context_timers.values(), [])

    def call(self):
        for timer in self.get_timers():
            if timer.due():
                timer.finish()
                self.events.on("timer.%s" % timer.name).call(timer=timer,
                    **timer.kwargs)
                if timer.done():
                    self._remove(timer)

    def purge_context(self, context):
        if context in self.context_timers:
            del self.context_timers[context]
