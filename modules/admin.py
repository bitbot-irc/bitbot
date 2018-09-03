

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        events.on("received.command.changenickname").hook(
            self.change_nickname, permission="changenickname",
            min_args=1, help="Change my nickname", usage="<nickname>")
        events.on("received.command.raw").hook(self.raw,
            permission="raw", min_args=1, usage="<raw line>",
            help="Send a raw IRC line through the bot")
        events.on("received.command.part").hook(self.part,
            permission="part", min_args=1, help="Part from a channel",
            usage="<#channel>")
        events.on("received.command.reconnect").hook(self.reconnect,
            permission="reconnect", help="Reconnect from this network")

    def change_nickname(self, event):
        nickname = event["args_split"][0]
        event["server"].send_nick(nickname)

    def raw(self, event):
        event["server"].send(event["args"])

    def part(self, event):
        event["server"].send_part(event["args_split"][0])

    def reconnect(self, event):
        event["server"].send_quit("Reconnecting")
