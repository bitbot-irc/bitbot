

class Module(object):
    def __init__(self, bot):
        bot.events.on("received.numeric.001").hook(
            self.on_connect)
        bot.events.on("self.join").hook(self.on_join)
        bot.events.on("self.kick").hook(self.on_kick)

    def on_connect(self, event):
        channels =  event["server"].get_setting("autojoin", [])
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

    def on_join(self, event):
        channels = event["server"].get_setting("autojoin", [])
        if not event["channel"].name in channels:
            channels.add(event["channel"].name)
            event["server"].set_setting("autojoin", channels)

    def on_kick(self, event):
        channels = event["server"].get_setting("autojoin", [])
        if event["channel"].name in channels:
            channels.remove(event["channel"].name)
            event["server"].set_setting("autojoin", channels)
