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

        current_schedule = [now.minute, now.hour]

        events = self.events.on("cron")
        for cron in events.get_hooks():
            schedule = cron.get_kwarg("schedule").split(" ")

            due = True
            for i, schedule_part in enumerate(schedule):
                current_part = current_schedule[i]
                if schedule_part.startswith("*/"):
                    schedule_step = int(schedule_part.split("*/", 1)[1])
                    if (current_part%schedule_step) == 0:
                        continue
                elif schedule_part == "*":
                    continue
                elif int(current_part) == schedule_part:
                    continue

                due = False
                break

            if due:
                cron.call(events.make_event())
