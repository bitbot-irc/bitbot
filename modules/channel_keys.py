from src import ModuleManager, utils

@utils.export("channelset", utils.Setting("key", "Channel key (password)",
    example="hunter2"))
class Module(ModuleManager.BaseModule):
    def _get_key(self, server, channel_name):
        channel_id = server.channels.get_id(channel_name)
        return self.bot.database.channel_settings.get(channel_id, "key", None)

    @utils.hook("preprocess.send.join")
    def preprocess_send_join(self, event):
        if event["line"].args:
            channels = event["line"].args[0].split(",")
            keys = event["line"].args[1:]

            with_keys = {}
            for channel in channels:
                if keys:
                    with_keys[channel] = keys.pop(0)
                else:
                    with_keys[channel] = self._get_key(event["server"], channel)

            channels_out = []
            keys_out = []

            # sort such that channels with keys are at the start
            for channel_name, key in sorted(with_keys.items(),
                    key=lambda item: not bool(item[1])):
                channels_out.append(channel_name)
                if key:
                    keys_out.append(key)
            event["line"].args[0] = ",".join(channels_out)
            event["line"].args[1:] = keys_out
