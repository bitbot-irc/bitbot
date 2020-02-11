import datetime, time
from src import ModuleManager, utils

TIMESTAMP_BOUNDS = [
    [0, 59],
    [0, 23],
    [1, 31],
    [1, 12],
    [0, 6],
]

class Module(ModuleManager.BaseModule):
    def on_load(self):
        now = datetime.datetime.utcnow()
        next_minute = now.replace(second=0, microsecond=0)
        next_minute += datetime.timedelta(minutes=1)
        until = time.time()+((next_minute-now).total_seconds())
        self.timers.add("cron", self._minute, 60, until)

    def _minute(self, timer):
        now = datetime.datetime.utcnow().replace(second=0, microsecond=0)
        timer.redo()

        timestamp = [now.minute, now.hour, now.day, now.month,
            now.isoweekday()%7]

        events = self.events.on("cron")
        def _check(schedule):
            return self._schedule_match(timestamp, schedule.split(" "))
        event = events.make_event(schedule=_check)

        for cron in events.get_hooks():
            schedule = cron.get_kwarg("schedule", None)
            if schedule and not _check(schedule):
                continue
            else:
                cron.call(event)

    def _schedule_match(self, timestamp, schedule):
        items = enumerate(zip(timestamp, schedule))
        for i, (timestamp_part, schedule_part) in items:
            if not self._schedule_match_part(i, timestamp_part, schedule_part):
                return False
        return True

    def _schedule_match_part(self, i, timestamp_part, schedule_part):
        if "," in schedule_part:
            for schedule_part in schedule_part.split(","):
                if self._schedule_match_part([timestamp_part], [schedule_part]):
                    return True

        elif "/" in schedule_part:
            range_s, _, step = schedule_part.partition("/")
            if "-" in range_s:
                range_min, _, range_max = range_s.partition("-")
                range_min = int(range_min)
                range_max = int(range_max)
            else:
                range_min, range_max = TIMESTAMP_BOUNDS[i]

            if (range_min <= timestamp_part <= range_max and
                    ((timestamp_part-range_min)%int(step)) == 0):
                return True

        elif "-" in schedule_part:
            left, right = schedule_part.split("-", 1)
            return int(left) <= timestamp_part <= int(right)

        elif schedule_part == "*":
            return True

        elif timestamp_part == int(schedule_part):
            return True

        return False
