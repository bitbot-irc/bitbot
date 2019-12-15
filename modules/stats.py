#--depends-on commands

import time
from bitbot import ModuleManager, utils

HIDDEN_MODES = set(["s", "p"])

class Module(ModuleManager.BaseModule):
    def _uptime(self):
        return utils.datetime.to_pretty_time(
            int(time.time()-self.bot.start_time))

    @utils.hook("received.command.uptime")
    def uptime(self, event):
        """
        :help: Show my uptime
        """
        event["stdout"].write("Uptime: %s" % self._uptime())
    @utils.hook("api.get.uptime")
    def uptime_api(self, event):
        return self._uptime()

    def _stats(self):
        networks = {}

        for server in self.bot.servers.values():
            networks[server.alias.lower()] = [len(server.channels),
                len(server.users)]

        return networks

    def _plural(self, s, count):
        return "%s%s" % (s, "" if count == 1 else "s")

    @utils.hook("received.command.stats")
    @utils.kwarg("help", "Show my network/channel/user stats")
    @utils.kwarg("usage", "[network]")
    def stats(self, event):
        networks = self._stats()

        if event["args"]:
            alias = event["args_split"][0].lower()
            if not alias in networks:
                raise utils.EventError("Unknown alias '%s'" % alias)

            channels, users = networks[alias]
            event["stdout"].write("On %s, I have %d %s and %d visible %s" %
                (alias, channels, self._plural("channel", channels), users,
                self._plural("user", users)))
        else:
            total_channels = 0
            total_users = 0
            for channels, users in networks.values():
                total_channels += channels
                total_users += users

            network_count = len(networks.keys())
            network_plural = self._plural("network", network_count)
            channel_plural = self._plural("channel", total_channels)
            user_plural = self._plural("user", total_users)
            event["stdout"].write(
                "I currently have %d %s, %d %s and %d visible %s" %
                (network_count, network_plural, total_channels, channel_plural,
                total_users, user_plural))

    @utils.hook("api.get.stats")
    def stats_api(self, event):
        networks, channels, users = self._stats()
        return {"networks": networks, "channels": channels, "users": users}

    def _server_stats(self, server):
        return {
            "hostname": server.connection_params.hostname,
            "port": server.connection_params.port,
            "tls": server.connection_params.tls,
            "alias": server.connection_params.alias,
            "hostmask": server.hostmask(),
            "users": len(server.users),
            "bytes-written": server.socket.bytes_written,
            "bytes-read": server.socket.bytes_read,
            "connected-since": server.socket.connect_time,
            "channels": {
                c.name: self._channel_stats(c) for c in server.channels
            },
            "capabilities": list(server.agreed_capabilities),
            "version": server.version
        }

    @utils.hook("api.get.servers")
    def servers_api(self, event):
        if event["args"]:
            server_id = event["args"][0]
            if not server_id.isdigit():
                return None
            server_id = int(server_id)

            server = self.bot.get_server_by_id(server_id)
            if not server:
                return None
            return self._server_stats(server)
        else:
            servers = {}
            for server in self.bot.servers.values():
                servers[server.id] = self._server_stats(server)
            return servers

    def _channel_stats(self, channel):
        setter = None
        if not channel.topic_setter == None:
            setter = channel.topic_setter.nickname
        return {
            "users": sorted([user.nickname for user in channel.users],
                key=lambda nickname: nickname.lower()),
            "topic": channel.topic,
            "topic-set-at": channel.topic_time,
            "topic-set-by": setter,
            "modes": channel.mode_str()
        }
    @utils.hook("api.get.channels")
    def channels_api(self, event):
        if event["args"]:
            server_id = event["args"][0]
            if not server_id.isdigit():
                return None
            server_id = int(server_id)

            server = self.bot.get_server_by_id(server_id)
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

    @utils.hook("received.command.channels")
    @utils.kwarg("help",
        "List all the channel I'm in on this network (* = hidden)")
    @utils.kwarg("permission", "listchannels")
    def channels_command(self, event):
        channels = []
        for channel in event["server"].channels.values():
            name = channel.name
            hidden = bool(HIDDEN_MODES&set(channel.modes.keys()))
            if hidden:
                if event["is_channel"] and not channel == event["target"]:
                    continue
                name = "*%s" % name
            channels.append(name)

        event["stdout"].write("Current channels: %s" %
            " ".join(sorted(channels)))

    @utils.hook("received.command.servers")
    @utils.kwarg("private_only", True)
    @utils.kwarg("help", "List all servers (* = connected)")
    @utils.kwarg("permission", "listservers")
    def servers_command(self, event):
        servers = []
        for id, alias in self.bot.database.servers.get_all():
            if not self.bot.get_server_by_id(id) == None:
                alias = "*%s" % alias
            servers.append(alias)
        event["stdout"].write("Servers: %s" % ", ".join(sorted(servers)))

    @utils.hook("api.get.modules")
    def modules_api(self, event):
        return list(self.bot.modules.modules.keys())
