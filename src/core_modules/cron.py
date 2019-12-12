import datetime, time
from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def on_load(self):
        now = datetime.datetime.utcnow()
        next_minute = now.replace(minute=now.minute+1, second=0, microsecond=0)
        until = time.time()+(next_minute-now).total_seconds()
        self.timers.add("cron", self._minute, 60, until)

    def _minute(self, timer):
        now = datetime.datetime.utcnow().replace(second=0, microsecond=0)
        timer.redo()

        timestamp = [now.minute, now.hour]

        events = self.events.on("cron")
        event = events.make_event()
        for cron in events.get_hooks():
            schedule = cron.get_kwarg("schedule").split(" ")

            if self._schedule_match(timestamp, schedule):
                cron.call(event)

    def _schedule_match(self, timestamp, schedule):
        for i, schedule_part in enumerate(schedule):
            timestamp_part = timestamp[i]
            if not self._schedule_match_part(timestamp_part, schedule_part):
                return False
        return True

    def _schedule_match_part(self, timestamp_part, schedule_part):
        if "," in schedule_part:
            for schedule_part in schedule_part.split(","):
                if self._match([timestamp_part], [schedule_part]):
                    return True

        elif schedule_part.startswith("*/"):
            schedule_step = int(schedule_part.split("*/", 1)[1])
            if (timestamp_part%schedule_step) == 0:
                return True

        elif "-" in schedule_part:
            left, right = schedule_part.split("-", 1)
            return int(left) <= timestamp_part <= int(right)

        elif schedule_part == "*":
            return True

        elif timestamp_part == int(schedule_part):
            return True

        return False
