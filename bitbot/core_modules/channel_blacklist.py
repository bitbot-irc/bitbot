from bitbot import EventManager, ModuleManager, utils

@utils.export("channelset", utils.BoolSetting("blacklist",
    "Refuse to join a given channel"))
class Module(ModuleManager.BaseModule):
    @utils.hook("preprocess.send.join")
    @utils.kwarg("priority", EventManager.PRIORITY_HIGH)
    def preprocess_send_join(self, event):
        if event["line"].args:
            channels = event["line"].args[0].split(",")
            keys = event["line"].args[1:]

            changed = False
            channels_out = []
            for channel_name in filter(None, channels):
                id = event["server"].channels.get_id(channel_name, create=False)
                if not id == None and self.bot.database.channel_settings.get(
                        id, "blacklist", False):
                    changed = True
                    if keys:
                        keys.pop(0)
                else:
                    key = None
                    if keys:
                        key = keys.pop(0)
                    channels_out.append([channel_name, key])

            if changed:
                if not channels_out:
                    event["line"].invalidate()
                else:
                    channels = [c[0] for c in channels_out]
                    keys = [c[1] for c in channels_out if c[1]]
                    event["line"].args[0] = ",".join(channels)
                    event["line"].args[1:] = keys

    @utils.hook("received.join")
    def on_join(self, event):
        if event["channel"].get_setting("blacklist", False):
            event["channel"].send_part()
