import time

class Timer(object):
    def __init__(self, bot, event_name, delay, **kwargs):
        self.bot = bot
        self.event_name = event_name
        self.delay = delay
        self.kwargs = kwargs
        self._done = False
        self.call_count = 0

    def set_started_time(self):
        self.started_time = time.time()

    def due(self):
        return self.time_left() <= 0

    def time_left(self):
        return (self.started_time+self.delay)-time.time()

    def call(self):
        self._done = True
        self.call_count +=1
        self.bot.events.on("timer").on(self.event_name).call(
            timer=self, **self.kwargs)

    def redo(self):
        self._done = False
        self.set_started_time()

    def done(self):
        return self._done
