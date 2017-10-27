

class Module(object):
    def __init__(self, bot):
        bot.events.on("self").on("part").hook(self.on_self_part)
        bot.events.on("self").on("join").hook(self.on_join)
        bot.events.on("received").on("numeric").on("366").hook(
            self.on_identify_trigger)
        bot.events.on("received").on("numeric").on("001").hook(
            self.on_identify_trigger)

    def on_self_part(self, event):
        pass

    def on_join(self, event):
        channels = set(event["server"].get_setting("autojoin", []))
        channels.add(event["channel"].name)
        event["server"].set_setting("autojoin", list(channels))

    def on_identify_trigger(self, event):
        if event["number"]=="001" and not event["server"].sasl_success: return
        if event["line_split"][3].lower() == "#bitbot" or event["number"]=="001":
            channels =  event["server"].get_setting("autojoin", [])
            chan_keys = event["server"].get_setting("channel_keys", {})
            channels_sorted = sorted(channels,
                key=lambda x: 0 if x in chan_keys else 1)

            keys_sorted = map(lambda x: x[1],
                sorted(chan_keys.items(),
                    key=lambda x: channels_sorted.index(x[0])))
            event["server"].send_join(
                ",".join(channels_sorted), ",".join(keys_sorted))

