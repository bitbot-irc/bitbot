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
    def _write_line(self, channel, line):
        channel.__log_file.write("%s\n" % line)
    def _write(self, channel, filename, key, line):
        if not hasattr(channel, "__log_file"):
            channel.__log_file = utils.io.open(filename, "a")
            channel.__log_rsa = None
            channel.__log_aes = None

        if key and not key == channel.__log_rsa:
            aes_key = utils.security.aes_key()
            channel.__log_rsa = key
            channel.__log_aes = aes_key

            aes_key_line = utils.security.rsa_encrypt(key, aes_key)
            self._write_line(channel, "\x03%s" % aes_key_line)

        if not channel.__log_aes == None:
            line = "\x04%s" % utils.security.aes_encrypt(
                channel.__log_aes, line)
        self._write_line(channel, line)

    def _log(self, server, channel, line):
        if self._enabled(server, channel):
            filename = self._file(str(server), str(channel))
            timestamp = utils.datetime.format.datetime_human(
                datetime.datetime.now())
            log_line = "%s %s" % (timestamp, line)
            self._write(channel, filename, self.bot.config.get("log-key"),
                log_line)

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
    @utils.hook("formatted.account")
    def on_formatted(self, event):
        if event["channel"]:
            self._log(event["server"], event["channel"], event["line"])
        elif event["user"]:
            for channel in event["user"].channels:
                self._log(event["server"], channel, event["line"])

