#--depends-on commands
#--depends-on permissions

from bitbot import IRCLine, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.nick", min_args=1)
    def change_nickname(self, event):
        """
        :help: Change my nickname
        :usage: <nickname>
        :permission: changenickname
        """
        nickname = event["args_split"][0]
        event["server"].send_nick(nickname)

    @utils.hook("received.command.raw", min_args=1)
    def raw(self, event):
        """
        :help: Send a line of raw IRC data
        :usage: <raw line>
        :permission: raw
        """
        if IRCLine.is_human(event["args"]):
            line = IRCLine.parse_human(event["args"])
        else:
            line = IRCLine.parse_line(event["args"])
        line = event["server"].send(line)

        if not line == None:
            event["stdout"].write("Sent: %s" % line.parsed_line.format())
        else:
            event["stderr"].write("Line was filtered")

    @utils.hook("received.command.part")
    def part(self, event):
        """
        :help: Part from the current or given channel
        :usage: [channel]
        :permission: part
        """
        if event["args"]:
            target = event["args_split"][0]
        elif event["is_channel"]:
            target = event["target"].name
        else:
            event["stderr"].write("No channel provided")
        event["server"].send_part(target)

    def _id_from_alias(self, alias):
        return self.bot.database.servers.get_by_alias(alias)
    def _server_from_alias(self, alias):
        id, server = self._both_from_alias(alias)
        return server
    def _both_from_alias(self, alias):
        id = self._id_from_alias(alias)
        if id == None:
            raise utils.EventError("Unknown server alias")
        return id, self.bot.get_server_by_id(id)

    @utils.hook("received.command.reconnect")
    def reconnect(self, event):
        """
        :help: Reconnect to the current network
        :permission: reconnect
        """
        server = event["server"]
        alias = str(event["server"])
        if event["args"]:
            alias = event["args_split"][0]
            server = self._server_from_alias(alias)

        if server:
            line = server.send_quit("Reconnecting")
            line.events.on("send").hook(lambda e: self.bot.reconnect(
                server.id, server.connection_params))
            if not server == event["server"]:
                event["stdout"].write("Reconnecting to %s" % alias)
        else:
            event["stdout"].write("Not connected to %s" % alias)

    @utils.hook("received.command.connect", min_args=1)
    def connect(self, event):
        """
        :help: Connect to a network
        :usage: <server id>
        :permission: connect
        """
        alias = event["args_split"][0]
        server = self._server_from_alias(alias)
        if server:
            raise utils.EventError("Already connected to %s" % str(server))

        server = self.bot.add_server(self._id_from_alias(alias))
        event["stdout"].write("Connecting to %s" % str(server))

    @utils.hook("received.command.disconnect")
    def disconnect(self, event):
        """
        :help: Disconnect from a server
        :usage: [server id]
        :permission: disconnect
        """
        server = event["server"]
        id = -1
        alias = str(event["server"])
        if event["args"]:
            alias = event["args_split"][0]
            id, server = self._both_from_alias(alias)

        if not server == None:
            alias = str(server)
            server.disconnect()
            self.bot.disconnect(server)
        elif id in self.bot.reconnections:
            self.bot.reconnections[id].cancel()
            del self.bot.reconnections[id]
        else:
            raise utils.EventError("Server not connected")

        event["stdout"].write("Disconnected from %s" % alias)

    @utils.hook("received.command.shutdown")
    def shutdown(self, event):
        """
        :help: Shutdown bot
        :usage: [reason]
        :permission: shutdown
        """
        reason = event["args"] or ""
        for server in self.bot.servers.values():
            line = server.send_quit(reason)
            line.events.on("send").hook(self._shutdown_hook(server))
    def _shutdown_hook(self, server):
        def shutdown(e):
            server.disconnect()
            self.bot.disconnect(server)
        return shutdown

    @utils.hook("received.command.addserver", min_args=3)
    def add_server(self, event):
        """
        :help: Add a new server
        :usage: <alias> <hostname>:[+]<port> <nickname>!<username>[@<bindhost>]
        :permission: addserver
        """
        alias = event["args_split"][0]
        hostname, sep, port = event["args_split"][1].partition(":")
        tls = port.startswith("+")
        port = port.lstrip("+")

        if not hostname or not port or not port.isdigit():
            raise utils.EventError("Please provide <hostname>:[+]<port>")
        port = int(port)

        hostmask = IRCLine.parse_hostmask(event["args_split"][2])
        nickname = hostmask.nickname
        username = hostmask.username or nickname
        realname = nickname
        bindhost = hostmask.hostname or None

        try:
            server_id = self.bot.database.servers.add(alias, hostname, port, "",
                tls, bindhost, nickname, username, realname)
        except Exception as e:
            event["stderr"].write("Failed to add server")
            self.log.error("failed to add server \"%s\"", [alias],
                exc_info=True)
            return
        event["stdout"].write("Added server '%s'" % alias)

    @utils.hook("received.command.editserver")
    @utils.kwarg("min_args", 3)
    @utils.kwarg("help", "Edit server details")
    @utils.kwarg("usage", "<alias> <option> <value>")
    @utils.kwarg("permission", "editserver")
    def edit_server(self, event):
        alias = event["args_split"][0]
        server_id = self._id_from_alias(alias)
        if server_id == None:
            raise utils.EventError("Unknown server '%s'" % alias)

        option = event["args_split"][1].lower()
        value = " ".join(event["args_split"][2:])
        value_parsed = None

        if option == "hostname":
            value_parsed = value
        elif option == "port":
            if not value.isdigit():
                raise utils.EventError("Invalid port")
            value_parsed = int(value.lstrip("0"))
        elif option == "tls":
            value_lower = value.lower()
            if not value_lower in ["yes", "no"]:
                raise utils.EventError("TLS should be either 'yes' or 'no'")
            value_parsed = value_lower == "yes"
        elif option == "password":
            value_parsed = value
        elif option == "bindhost":
            value_parsed = value
        elif option in ["nickname", "username", "realname"]:
            value_parsed = value
        else:
            raise utils.EventError("Unknown option '%s'" % option)

        self.bot.database.servers.edit(server_id, option, value_parsed)
        event["stdout"].write("Set %s for %s" % (option, alias))
