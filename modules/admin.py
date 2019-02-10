from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.changenickname", min_args=1)
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
        event["server"].send(event["args"])

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

    @utils.hook("received.command.reconnect")
    def reconnect(self, event):
        """
        :help: Reconnect to the current network
        :permission: reconnect
        """
        line = event["server"].send_quit("Reconnecting")
        line.on_send(lambda: self.bot.reconnect(
            event["server"].id, event["server"].connection_params))

    @utils.hook("received.command.connect", min_args=1)
    def connect(self, event):
        """
        :help: Connect to a network
        :usage: <server id>
        :permission: connect
        """
        id = event["args_split"][0]
        if not id.isdigit():
            raise utils.EventError("Please provide a numeric server ID")

        id = int(id)
        if not self.bot.database.servers.get(id):
            raise utils.EventError("Unknown server ID")

        existing_server = self.bot.get_server(id)
        if existing_server:
            raise utils.EventError("Already connected to %s" % str(
                existing_server))

        server = self.bot.add_server(id)
        event["stdout"].write("Connecting to %s" % str(server))

    @utils.hook("received.command.disconnect")
    def disconnect(self, event):
        """
        :help: Disconnect from a server
        :usage: [server id]
        :permission: disconnect
        """
        id = event["server"].id
        if event["args"]:
            id = event["args_split"][0]
            if not id.isdigit():
                raise utils.EventError("Please provide a numeric server ID")

            id = int(id)
            if not self.bot.database.servers.get(id):
                raise utils.EventError("Unknown server ID")
        server = self.bot.get_server(id)
        server.disconnect()
        self.bot.disconnect(server)

    @utils.hook("received.command.shutdown")
    def shutdown(self, event):
        """
        :help: Shutdown bot
        :usage: [reason]
        :permission: shutdown
        """
        reason = event["args"] or ""
        for server in self.bot.servers:
            line = server.send_quit(reason)
            line.on_send(self._shutdown_hook(server))
    def _shutdown_hook(self, server):
        return lambda: self.bot.disconnect(server)
