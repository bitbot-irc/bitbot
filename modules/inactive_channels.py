import datetime
from src import ModuleManager, utils

PRUNE_TIMEDELTA = datetime.timedelta(weeks=4)

SETTING_NAME = "inactive-prune"
SETTING = utils.IntRangeSetting(0, None, SETTING_NAME,
    "Amount of days of inactivity before we leave a channel")

MODE_SETTING_NAME = "inactive-prune-modes"
MODE_SETTING = utils.BoolSetting(MODE_SETTING_NAME,
    "Whether or not we will leave inactive channels that we have a mode in")

@utils.export("botset", SETTING)
@utils.export("serverset", SETTING)
@utils.export("serverset", MODE_SETTING)
@utils.export("channelset", MODE_SETTING)

@utils.export("channelset", utils.BoolSetting(SETTING_NAME,
    "Whether or not to leave this channel when it is inactive"))
class Module(ModuleManager.BaseModule):
    def _get_timestamp(self, channel):
        return channel.get_setting("last-message", None)
    def _set_timestamp(self, channel):
        channel.set_setting("last-message",
            utils.datetime.format.iso8601(utils.datetime.utcnow()))
    def _del_timestamp(self, channel):
        channel.del_setting("last-message")

    @utils.hook("new.channel")
    def new_channel(self, event):
        if self._get_timestamp(event["channel"]) == None:
            self._set_timestamp(event["channel"])

    @utils.hook("cron")
    @utils.kwarg("schedule", "0")
    def hourly(self, event):
        parts = []
        now = utils.datetime.utcnow()
        botwide_days = self.bot.get_setting(SETTING_NAME, None)
        botwide_mode_setting = self.bot.get_setting(MODE_SETTING_NAME, False)

        for server in self.bot.servers.values():
            serverwide_days = server.get_setting(SETTING_NAME, botwide_days)
            if serverwide_days == None:
                continue

            mode_setting = server.get_setting(
                MODE_SETTING_NAME, botwide_mode_setting)
            our_user = server.get_user(server.nickname)

            for channel in server.channels:
                if (not channel.get_setting(SETTING_NAME, True) or
                        not mode_setting and channel.get_user_modes(our_user)):
                    continue

                timestamp = self._get_timestamp(channel)
                if timestamp:
                    dt = utils.datetime.parse.iso8601(timestamp)
                    if (now-dt).days >= serverwide_days:
                        parts.append([server, channel])

        for server, channel in parts:
            self.log.warn("Leaving %s:%s due to channel inactivity",
                [str(server), str(channel)])
            channel.send_part("Channel inactive")
            self._del_timestamp(channel)

    @utils.hook("send.message.channel")
    @utils.hook("received.message.channel")
    def channel_message(self, event):
        self._set_timestamp(event["channel"])
