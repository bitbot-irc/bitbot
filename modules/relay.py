from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("new.server")
    def new_server(self, event):
        event["server"]._relay_ignore = []

    def _get_relays(self, channel):
        return channel.get_setting("channel-relays", [])

    def _relay(self, event, channel):
        if ("parsed_line" in event and
                event["parsed_line"].id in event["server"]._relay_ignore):
            event["server"]._relay_ignore.remove(event["parsed_line"].id)
            return

        relays = self._get_relays(channel)
        for server_id, channel_name in relays:
            server = self.bot.get_server_by_id(server_id)
            if not server == None and channel_name in server.channels:
                other_channel = server.channels.get(channel_name)

                if not self._has_relay_for(other_channel, event["server"].id,
                        channel.name):
                    self.log.warn(
                        "Tried to relay with one-way config: %s%s -> %s%s",
                        [str(event["server"]), channel.name, str(server),
                        other_channel.name])
                    return

                relay_prefix_channel = ""
                if not other_channel.name == channel.name:
                    relay_prefix_channel = channel.name

                relay_message = "[relay/%s%s] %s" % (str(event["server"]),
                    relay_prefix_channel, event["line"])

                message = utils.irc.protocol.privmsg(other_channel.name,
                    relay_message)
                server._relay_ignore.append(message.id)
                server.send(message)

    def _has_relay_for(self, channel, server_id, channel_name):
        relays = self._get_relays(channel)
        for other_server_id, other_channel_name in relays:
            if (other_server_id == server_id and
                    other_channel_name == channel_name):
                return True
        return False

    @utils.hook("formatted.message.channel")
    @utils.hook("formatted.notice.channel")
    @utils.hook("formatted.join")
    @utils.hook("formatted.part")
    @utils.hook("formatted.nick")
    @utils.hook("formatted.mode.channel")
    @utils.hook("formatted.kick")
    @utils.hook("formatted.quit")
    @utils.hook("formatted.rename")
    def formatted(self, event):
        if event["channel"]:
            self._relay(event, event["channel"])
        elif event["user"]:
            for channel in event["user"].channels:
                self._relay(event, channel)

    @utils.hook("received.command.relay", min_args=3, channel_only=True)
    def relay(self, event):
        """
        :help: Edit configured relays
        :usage: add <server> <channel>
        :usage: remove <server> <channel>
        :permission: relay
        """
        target_server_alias = event["args_split"][1].lower()
        target_server = self.bot.get_server_by_alias(target_server_alias)

        if target_server == None:
            raise utils.EventError("Unknown server provided")

        current_relays = self._get_relays(event["target"])
        target_server_relays = list(filter(
            lambda relay: relay[0] == target_server.id, current_relays))
        target_relays = list(map(lambda relay: relay[1], target_server_relays))

        target_channel_name = target_server.irc_lower(event["args_split"][2])

        changed = False
        message = None

        subcommand = event["args_split"][0].lower()
        if subcommand == "add":
            if target_channel_name in target_relays:
                raise utils.EventError("Already relaying to that channel")

            if not target_channel_name in target_server.channels:
                raise utils.EventError("Cannot find the provided channel")

            current_relays.append((target_server.id, target_channel_name))

            message = "Relay added"
        elif subcommand == "remove":
            if not target_channel_name in target_relays:
                raise utils.EventError("I'm not relaying to that channel")

            for i, (server_id, channel_name) in enumerate(current_relays):
                if (server_id == target_server.id and
                        channel_name == target_channel_name):
                    current_relays.pop(i)
                    break

            message = "Removed relay"
        else:
            raise utils.EventError("Unknown subcommand '%s'" % subcommand)


        event["target"].set_setting("channel-relays", current_relays)
        event["stdout"].write(message)
