import time
from src import ModuleManager, utils

SECONDS_MAX = utils.SECONDS_WEEKS*8
SECONDS_MAX_DESCRIPTION = "8 weeks"

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.in", min_args=2)
    def in_command(self, event):
        """
        :help: Set a reminder
        :usage: <time> <message>
        """
        seconds = utils.from_pretty_time(event["args_split"][0])
        message = " ".join(event["args_split"][1:])
        if seconds:
            if seconds <= SECONDS_MAX:
                due_time = int(time.time())+seconds

                self.timers.add_persistent("in", seconds, due_time=due_time,
                    target=event["target"].name, server_id=event["server"].id,
                    nickname=event["user"].nickname, message=message)
                event["stdout"].write("Saved")
            else:
                event["stderr"].write(
                    "The given time is above the max (%s)" % (
                    SECONDS_MAX_DESCRIPTION))
        else:
            event["stderr"].write(
                "Please provided a valid time above 0 seconds")

    @utils.hook("timer.in")
    def timer_due(self, event):
        server = self.bot.get_server(event["server_id"])
        if server:
            server.send_message(event["target"],
                "%s, this is your reminder: %s" % (
                event["nickname"], event["message"]))
