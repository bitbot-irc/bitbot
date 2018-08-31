import time, uuid

class Timer(object):
    def __init__(self, id, bot, events, event_name, delay,
            next_due=None, **kwargs):
        self.id = id
        self.bot = bot
        self.events = events
        self.event_name = event_name
        self.delay = delay
        if next_due:
            self.next_due = next_due
        else:
            self.set_next_due()
        self.kwargs = kwargs
        self._done = False
        self.call_count = 0

    def set_next_due(self):
        self.next_due = time.time()+self.delay

    def due(self):
        return self.time_left() <= 0

    def time_left(self):
        return self.next_due-time.time()

    def call(self):
        self._done = True
        self.call_count +=1
        self.events.on("timer").on(self.event_name).call(
            timer=self, **self.kwargs)

    def redo(self):
        self._done = False
        self.set_next_due()

    def done(self):
        return self._done
