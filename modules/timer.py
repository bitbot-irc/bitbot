#--depends-on commands

import time
from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _get_timer(self, user):
        return user.get_setting("timer", None)
    def _set_timer(self, user, timestamp: float):
        user.set_setting("timer", timestamp)
    def _del_timer(self, user):
        user.del_setting("timer")

    @utils.hook("received.command.starttimer")
    def start_timer(self, event):
        if self._get_timer(event["user"]):
            raise utils.EventError("You already have a timer")

        self._set_timer(event["user"], time.time())
        event["stdout"].write("Timer started")

    @utils.hook("received.command.stoptimer")
    def stop_timer(self, event):
        timer = self._get_timer(event["user"])
        if not timer:
            raise utils.EventError("No timer started")

        self._del_timer(event["user"])
        elapsed = time.time()-timer
        pretty = utils.to_pretty_time(int(elapsed))
        event["stdout"].write("Timer stopped at %s" % pretty)
