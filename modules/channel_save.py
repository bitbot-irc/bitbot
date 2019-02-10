from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.numeric.001")
    def on_connect(self, event):
        channels = event["server"].get_setting("autojoin", [])
        if not channels:
            return

        chan_keys = event["server"].get_setting("channel_keys", {})
        channels_sorted = sorted(channels,
            key=lambda x: 0 if x in chan_keys else 1)

        keys_sorted = list(map(lambda x: x[1],
            sorted(chan_keys.items(),
            key=lambda x: channels_sorted.index(x[0]))))

        for i in range(len(channels_sorted)):
            channel = channels_sorted[i]
            key = None if len(keys_sorted) <= i else keys_sorted[i]
            event["server"].attempted_join[channel] = key

        event["server"].send_join(
            ",".join(channels_sorted), ",".join(keys_sorted))

    @utils.hook("self.join")
    def on_join(self, event):
        channels = event["server"].get_setting("autojoin", [])
        channel_name = event["server"].irc_lower(event["channel"].name)
        if not channel_name in channels:
            channels.append(channel_name)
            event["server"].set_setting("autojoin", channels)

    def _remove_channel(self, server, channel_name):
        channels = server.get_setting("autojoin", [])
        if channel_name in channels:
            channels.remove(channel_name)
            server.set_setting("autojoin", channels)

    @utils.hook("self.part")
    def on_part(self, event):
        self._remove_channel(event["server"], event["channel"].name)

    @utils.hook("self.kick")
    def on_kick(self, event):
        self._remove_channel(event["server"], event["channel"].name)
