import time
from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _uptime(self):
        return utils.to_pretty_time(int(time.time()-self.bot.start_time))

    @utils.hook("received.command.uptime")
    def uptime(self, event):
        """
        :help: Show my uptime
        """
        event["stdout"].write("Uptime: %s" % self._uptime())
    @utils.hook("api.uptime")
    def uptime_api(self, event):
        return self._uptime()

    def _stats(self):
        networks = len(self.bot.servers)
        channels = 0
        users = 0
        for server in self.bot.servers.values():
            channels += len(server.channels)
            users += len(server.users)
        return [networks, channels, users]

    @utils.hook("received.command.stats")
    def stats(self, event):
        """
        :help: Show my network/channel/user stats
        """
        networks, channels, users = self._stats()

        response = "I currently have %d network" % networks
        if networks > 1:
            response += "s"
        response += ", %d channel" % channels
        if channels > 1:
            response += "s"
        response += " and %d visible user" % users
        if users > 1:
            response += "s"

        event["stdout"].write(response)

    @utils.hook("api.stats")
    def stats_api(self, event):
        networks, channels, users = self._stats()
        return {"networks": networks, "channels": channels, "users": users}

    @utils.hook("api.servers")
    def servers_api(self, event):
        servers = {}
        for server in self.bot.servers.values():
            servers[server.id] = {
                "hostname": server.target_hostname,
                "port": server.port,
                "tls": server.tls,
                "alias": server.alias
            }
        return servers

    def _channel_stats(self, channel):
        return {
            "users": len(channel.users),
            "topic": channel.topic
        }
    @utils.hook("api.channels")
    def channels_api(self, event):
        if event["path"]:
            server_id = event["path"][0]
            if not server_id.isdigit():
                return None
            server_id = int(server_id)

            server = self.bot.get_server(server_id)
            if not server:
                return None
            channels = {}
            for channel in server.channels.values():
                channels[channel.name] = self._channel_stats(channel)
            return channels
        else:
            channels = {}
            for server in self.bot.servers.values():
                channels[server.id] = {}
                for channel in server.channels.values():
                    channels[server.id][str(channel)] = self._channel_stats(
                        channel)
            return channels

    @utils.hook("api.modules")
    def modules_api(self, event):
        return list(self.bot.modules.modules.keys())
