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
        event["server"].send_quit("Reconnecting")

    @utils.hook("received.command.connect", min_args=1)
    def connect(self, event):
        """
        :help: Connect to a network
        :usage: <server id>
        """
        id = event["args_split"][0]
        if not id.isdigit():
            event["stderr"].write("Please provide a numeric server ID")
            return

        id = int(id)
        if not self.bot.database.servers.get(id):
            event["stderr"].write("Unknown server ID")
            return

        existing_server = self.bot.get_server(id)
        if existing_server:
            event["stderr"].write("Already connected to %s" % str(
                existing_server))
            return
        server = self.bot.add_server(id)
        event["stdout"].write("Connecting to %s" % str(server))
