import datetime, os
from src import PollHook, utils

EXPIRATION = 60 # 1 minute

class LockFile(PollHook.PollHook):
    def __init__(self, database_location: str):
        self._lock_location = "%s.lock" % database_location
        self._next_lock = None

    def available(self):
        now = utils.datetime_utcnow()
        if os.path.exists(self._lock_location):
            with open(self._lock_location, "r") as lock_file:
                timestamp_str = lock_file.read().strip().split(" ", 1)[0]

            timestamp = utils.iso8601_parse(timestamp_str)

            if (now-timestamp).total_seconds() < EXPIRATION:
                return False

        return True

    def lock(self):
        with open(self._lock_location, "w") as lock_file:
            last_lock = utils.datetime_utcnow()
            lock_file.write("%s" % utils.iso8601_format(last_lock))
            self._next_lock = last_lock+datetime.timedelta(
                seconds=EXPIRATION/2)

    def next(self):
        return max(0, (self._next_lock-utils.datetime_utcnow()).total_seconds())
    def call(self):
        self.lock()

    def unlock(self):
        if os.path.isfile(self._lock_location):
            os.remove(self._lock_location)
