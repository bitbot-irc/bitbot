#--depends-on config
#--depends-on format_activity

import datetime, os.path
from src import ModuleManager, utils

SETTING = utils.BoolSetting("channel-log",
    "Enable/disable channel logging")

@utils.export("channelset",utils.BoolSetting("log",
    "Enable/disable channel logging"))
@utils.export("serverset", SETTING)
@utils.export("botset", SETTING)
class Module(ModuleManager.BaseModule):
    def _enabled(self, server, channel):
        return channel.get_setting("log",
            server.get_setting("channel-log",
            self.bot.get_setting("channel-log", False)))
    def _file(self, server_name, channel_name):
        # if a channel name has os.path.sep (e.g. "/") in it, the channel's log
        # file will create a subdirectory.
        #
        # to avoid this, we'll replace os.path.sep with "," (0x2C) as it is
        # forbidden in channel names.
        sanitised_name = channel_name.replace(os.path.sep, ",")
        return self.data_directory("%s/%s.log" % (server_name, sanitised_name))
    def _log(self, server, channel, line):
        if self._enabled(server, channel):
            with open(self._file(str(server), str(channel)), "a") as log:
                timestamp = utils.datetime.datetime_human(
                    datetime.datetime.now())
                log.write("%s %s\n" % (timestamp, line))

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
    @utils.hook("formatted.chghost")
    def on_formatted(self, event):
        if event["channel"]:
            self._log(event["server"], event["channel"], event["line"])
        elif event["user"]:
            for channel in event["user"].channels:
                self._log(event["server"], channel, event["line"])

