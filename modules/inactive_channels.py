import datetime
from src import ModuleManager, utils

PRUNE_TIMEDELTA = datetime.timedelta(weeks=2)
SETTING_NAME = "inactive-channels"
SETTING = utils.BoolSetting(SETTING_NAME,
    "Whether or not to leave inactive channels after 2 weeks")

@utils.export("botset", SETTING)
@utils.export("serverset", SETTING)
@utils.export("channelset", SETTING)
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
        botwide_setting = self.bot.get_setting(SETTING_NAME, False)

        for server in self.bot.servers.values():
            serverwide_setting = server.get_setting(
                SETTING_NAME, botwide_setting)
            if not serverwide_setting:
                continue

            for channel in server.channels:
                if not channel.get_setting(SETTING_NAME, serverwide_setting):
                    continue

                timestamp = self._get_timestamp(channel)
                if timestamp:
                    dt = utils.datetime.parse.iso8601(timestamp)
                    if (now-dt) >= PRUNE_TIMEDELTA:
                        parts.append([server, channel])

        for server, channel in parts:
            self.log.warn("Leaving %s:%s due to channel inactivity",
                [str(server), str(channel)])
            channel.send_part("Channel inactive")
            self._del_timestamp(channel)

    @utils.hook("received.message.channel")
    def channel_message(self, event):
        self._set_timestamp(event["channel"])
