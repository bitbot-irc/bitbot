import time, uuid

class Timer(object):
    def __init__(self, id, name, delay, next_due, kwargs):
        self.id = id
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

class Timers(object):
    def __init__(self, database, events, log):
        self.database = database
        self.events = events
        self.log = log
        self.timers = []

    def setup(self, timers):
        for name, timer in timers:
            id = name.split("timer-", 1)[1]
            self._add(timer["name"], timer["delay"], timer[
                "next-due"], id, False, timer["kwargs"])

    def _persist(self, timer):
        self.database.bot_settings.set("timer-%s" % timer.id, {
            "name": timer.name, "delay": timer.delay,
            "next-due": timer.next_due, "kwargs": timer.kwargs})
    def _remove(self, timer):
        self.timers.remove(timer)
        self.database.bot_settings.delete("timer-%s" % timer.id)

    def add(self, name, delay, next_due=None, **kwargs):
        self._add(name, delay, next_due, None, False, kwargs)
    def add_persistent(self, name, delay, next_due=None, **kwargs):
        self._add(name, delay, next_due, None, True, kwargs)
    def _add(self, name, delay, next_due, id, persist, kwargs):
        id = id or uuid.uuid4().hex
        timer = Timer(id, name, delay, next_due, kwargs)
        if persist:
            self._persist(timer)
        self.timers.append(timer)

    def next(self):
        times = filter(None, [timer.time_left() for timer in self.timers])
        if not times:
            return None
        return max(min(times), 0)

    def call(self):
        for timer in self.timers[:]:
            if timer.due():
                timer.finish()
                self.events.on("timer.%s" % timer.name).call(timer=timer,
                    **timer.kwargs)
                if timer.done():
                    self._remove(timer)
