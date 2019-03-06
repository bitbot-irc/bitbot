import datetime, os.path
from src import ModuleManager, utils

ROOT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
LOGS_DIRECTORY = os.path.join(ROOT_DIRECTORY, "logs")

@utils.export("channelset", {"setting": "log",
    "help": "Enable/disable channel logging",
    "validate": utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    def _log_file(self, server_name, channel_name):
        return open(os.path.join(LOGS_DIRECTORY,
            "%s%s.log" % (server_name, channel_name)), "a")
    def _log(self, event, channel):
        if channel.get_setting("log", False):
            with self._log_file(str(event["server"]), str(channel)) as log:
                timestamp = datetime.datetime.now().strftime("%x %X")
                log.write("%s %s\n" % (timestamp, event["raw_line"]))

    @utils.hook("formatted.message.channel")
    @utils.hook("formatted.notice.channel")
    @utils.hook("formatted.join")
    @utils.hook("formatted.part")
    @utils.hook("formatted.nick")
    @utils.hook("formatted.invite")
    @utils.hook("formatted.mode.channel")
    @utils.hook("formatted.topic")
    @utils.hook("formatted.topic-timestamp")
    @utils.hook("formatted.kick")
    @utils.hook("formatted.quit")
    @utils.hook("formatted.rename")
    def on_formatted(self, event):
        if event["channel"]:
            self._log(event, event["channel"])
        elif event["user"]:
            for channel in event["user"].channels:
                self._log(event, channel)
