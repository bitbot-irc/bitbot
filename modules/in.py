import time
import Utils

SECONDS_MAX = Utils.SECONDS_WEEKS*8
SECONDS_MAX_DESCRIPTION = "8 weeks"

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("command").on("in").hook(
            self.in_command, min_args=2,
            help="Set a reminder", usage="<time> <message>")
        bot.events.on("received").on("numeric").on("001").hook(
            self.on_connect)

    def on_connect(self, event):
        self.load_reminders(event["server"])

    def remove_timer(self, target, due_time, server_id, nickname, message):
        setting = "in-%s" % nickname
        reminders = self.bot.database.get_server_setting(server_id, setting, [])
        try:
            reminders.remove([target, due_time, server_id, nickname, message])
        except:
            print("failed to remove a reminder. huh.")
        if reminders:
            self.bot.database.set_server_setting(server_id,
                setting, reminders)
        else:
            self.bot.database.del_server_setting(server_id,
                setting)

    def load_reminders(self, server):
        reminders = server.find_settings("in-%")
        for user_reminders in reminders:
            for target, due_time, server_id, nickname, message in user_reminders[1]:
                time_left = due_time-time.time()
                if time_left > 0:
                    self.bot.add_timer(self.timer_due, time_left, target=target,
                        due_time=due_time, server_id=server_id, nickname=nickname,
                        message=message)
                else:
                    self.remove_timer(target, due_time, server_id, nickname,
                        message)

    def in_command(self, event):
        seconds = Utils.from_pretty_time(event["args_split"][0])
        message = " ".join(event["args_split"][1:])
        if seconds:
            if seconds <= SECONDS_MAX:
                due_time = int(time.time())+seconds

                setting = "in-%s" % event["user"].nickname
                reminders = event["server"].get_setting(setting, [])
                reminders.append([event["target"].name, due_time,
                    event["server"].id, event["user"].nickname, message])
                event["server"].set_setting(setting, reminders)

                self.bot.add_timer(self.timer_due, seconds,
                    target=event["target"].name, due_time=due_time,
                    server_id=event["server"].id, nickname=event["user"].nickname,
                    message=message)
                event["stdout"].write("Saved")
            else:
                event["stderr"].write(
                    "The given time is above the max (%s)" % (
                    SECONDS_MAX_DESCRIPTION))
        else:
            event["stderr"].write(
                "Please provided a valid time above 0 seconds")

    def timer_due(self, timer, **kwargs):
        for server in self.bot.servers.values():
            if kwargs["server_id"] == server.id:
                server.send_message(kwargs["target"],
                    "%s, this is your reminder: %s" % (
                    kwargs["nickname"], kwargs["message"]))
                break
        setting = "in-%s" % kwargs["nickname"]
        self.remove_timer(kwargs["target"], kwargs["due_time"],
            kwargs["server_id"], kwargs["nickname"], kwargs["message"])
