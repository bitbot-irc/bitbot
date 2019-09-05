from src import EventManager, ModuleManager, utils

@utils.export("channelset", utils.BoolSetting("blacklist",
    "Refuse to join a given channel"))
class Module(ModuleManager.BaseModule):
    @utils.hook("preprocess.send.join")
    @utils.kwarg("priority", EventManager.PRIORITY_HIGH)
    def preprocess_send_join(self, event):
        if event["line"].args:
            channels = event["line"].args[0].split(",")
            keys = event["line"].args[1:]

            remove = []
            for channel_name in channels:
                id = event["server"].channels.get_id(channel_name, create=False)
                if not id == None:
                    if self.bot.database.channel_settings.get(id, "blacklist",
                            False):
                        remove.append(channel_name)
                        if keys:
                            keys.pop(0)
            for channel_name in remove:
                channels.remove(channel_name)

            if remove:
                if not channels:
                    event["line"].invalidate()
                else:
                    event["line"].args[0] = ",".join(channels)
                    event["line"].args[1:] = keys
