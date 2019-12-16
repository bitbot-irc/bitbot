#--depends-on config

from bitbot import ModuleManager, utils

DELAY = 5

rejoin_setting = utils.BoolSetting("kick-rejoin",
    "Whether or not I should rejoin channels I get kicked from")
delay_setting = utils.IntSetting("kick-rejoin-delay",
    "Amount of seconds to wait before rejoining a channel")

@utils.export("serverset", rejoin_setting)
@utils.export("serverset", delay_setting)
@utils.export("channelset", rejoin_setting)
@utils.export("channelset", delay_setting)
class Module(ModuleManager.BaseModule):
    def _should_rejoin(self, server, channel):
        return channel.get_setting("kick-rejoin",
            server.get_setting("kick-rejoin", False))
    def _get_delay(self, server, channel):
        return channel.get_setting("kick-rejoin-delay",
            server.get_setting("kick-rejoin-delay", DELAY))

    @utils.hook("self.kick")
    def on_kick(self, event):
        if self._should_rejoin(event["server"], event["channel"]):
            delay = self._get_delay(event["server"], event["channel"])
            if delay == 0:
                self._rejoin(event["server"], event["channel"].name)
            else:
                self.timers.add("kick-rejoin",
                    self._timer(event["server"], event["channel"].name),
                    delay)

    def _timer(self, server, channel_name):
        return lambda timer: self._rejoin(server, channel_name)

    def _rejoin(self, server, channel_name):
        server.send_join(channel_name)
