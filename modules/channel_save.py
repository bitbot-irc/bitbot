from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.001")
    def on_connect(self, event):
        channels = event["server"].get_setting("autojoin", [])
        if channels:
                event["server"].send_joins(channels)

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
