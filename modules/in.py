#--depends-on commands
import time
from src import ModuleManager, utils

SECONDS_MAX = utils.datetime.SECONDS_WEEKS*8
SECONDS_MAX_DESCRIPTION = "8 weeks"

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.remindme", alias_of="in")
    @utils.hook("received.command.in", min_args=2)
    @utils.kwarg("help", "Set a reminder")
    @utils.kwarg("usage", "<time> <message>")
    def in_command(self, event):
        seconds = utils.datetime.parse.from_pretty_time(event["args_split"][0])
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
        server = self.bot.get_server_by_id(event["server_id"])
        if server:
            message = "%s: this is your reminder: %s" % (
                event["nickname"], event["message"])
            target = server.get_target(event["target"])
            self.events.on("send.stdout").call(target=target, module_name="In",
                server=server, message=message)

    @utils.hook("received.command.inlist")
    def in_list(self, event):
        """
        :help: List reminders
        :usage: [index]
        """
        timers = self.timers.find_all("in")
        found = []
        for timer in timers:
            nickname_match = (event["server"].irc_lower(
                timer.kwargs["nickname"]) == event["user"].nickname_lower)
            target_match = timer.kwargs["target"] == event["target"].name

            if nickname_match and target_match:
                found.append(timer)

        if len(event["args_split"]) > 0:
            index = event["args_split"][0]
            if not index.isdigit() or index == "0":
                raise utils.EventError("Please provide a valid reminder index")

            index = int(index)
            actual_index = index-1
            if actual_index > len(found):
                raise utils.EventError("You do not have that many reminders")

            timer = found[actual_index]
            event["stdout"].write("Reminder %d: %s" % (index,
                timer.kwargs["message"]))
        else:
            event["stdout"].write("%s: you have %d reminders" % (
                event["user"].nickname, len(found)))
