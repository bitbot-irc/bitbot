import datetime, os
from . import PollHook, utils

EXPIRATION = 60 # 1 minute

class LockFile(PollHook.PollHook):
    def __init__(self, filename: str):
        self._filename = filename
        self._next_lock = None

    def available(self):
        now = utils.datetime.utcnow()
        if os.path.exists(self._filename):
            with open(self._filename, "r") as lock_file:
                timestamp_str = lock_file.read().strip().split(" ", 1)[0]

            timestamp = utils.datetime.iso8601_parse(timestamp_str)

            if (now-timestamp).total_seconds() < EXPIRATION:
                return False

        return True

    def lock(self):
        with open(self._filename, "w") as lock_file:
            last_lock = utils.datetime.utcnow()
            lock_file.write("%s" % utils.datetime.iso8601_format(last_lock))
            self._next_lock = last_lock+datetime.timedelta(
                seconds=EXPIRATION/2)

    def next(self):
        return max(0,
            (self._next_lock-utils.datetime.utcnow()).total_seconds())
    def call(self):
        self.lock()

    def unlock(self):
        if os.path.isfile(self._filename):
            os.remove(self._filename)
