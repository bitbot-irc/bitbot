from src import ModuleManager, Utils

class Module(ModuleManager.BaseModule):
    @Utils.hook("received.command.changenickname",
        permission="changenickname", min_args=1, usage="<nickname>")
    def change_nickname(self, event):
        """
        Change my nickname
        """
        nickname = event["args_split"][0]
        event["server"].send_nick(nickname)

    @Utils.hook("received.command.raw", permission="raw", min_args=1,
        usage="<raw line>")
    def raw(self, event):
        """
        Send a line of raw IRC data
        """
        event["server"].send(event["args"])

    @Utils.hook("received.command.part", permission="part", usage="[#channel]")
    def part(self, event):
        """
        Part from the current or given channel
        """
        if event["args"]:
            target = event["args_split"][0]
        elif event["is_channel"]:
            target = event["target"].name
        else:
            event["stderr"].write("No channel provided")
        event["server"].send_part(target)

    @Utils.hook("received.command.reconnect", permission="reconnect")
    def reconnect(self, event):
        """
        Reconnect to the current network
        """
        event["server"].send_quit("Reconnecting")
