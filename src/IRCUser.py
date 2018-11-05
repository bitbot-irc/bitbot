import typing, uuid
from src import IRCBot, IRCChannel, IRCBuffer, IRCObject, IRCServer, utils

class User(IRCObject.Object):
    def __init__(self, nickname: str, id: int, server: "IRCServer.Server",
            bot: "IRCBot.Bot"):
        self.name = ""
        self.nickname = ""
        self.nickname_lower = ""

        self.server = server
        self.set_nickname(nickname)
        self._id = id
        self.username = None
        self.hostname = None
        self.realname = None
        self.bot = bot
        self.channels = set([]) # type: typing.Set[IRCChannel.Channel]

        self.identified_account = None
        self.identified_account_override = None

        self.identified_account_id = None
        self.identified_account_id_override = None
        self.away = False
        self.buffer = IRCBuffer.Buffer(bot, server)

    def __repr__(self) -> str:
        return "IRCUser.User(%s|%s)" % (self.server.name, self.name)
    def __str__(self) -> str:
        return self.nickname

    def get_id(self)-> int:
        return (self.identified_account_id_override or
            self.identified_account_id or self._id)
    def get_identified_account(self) -> typing.Optional[str]:
        return (self.identified_account_override or self.identified_account)

    def set_nickname(self, nickname: str):
        self.name = self.nickname_lower
        self.nickname = nickname
        self.nickname_lower = utils.irc.lower(self.server.case_mapping,
            nickname)
    def join_channel(self, channel: "IRCChannel.Channel"):
        self.channels.add(channel)
    def part_channel(self, channel: "IRCChannel.Channel"):
        self.channels.remove(channel)

    def set_setting(self, setting: str, value: typing.Any):
        self.bot.database.user_settings.set(self.get_id(), setting, value)
    def get_setting(self, setting: str, default: typing.Any=None) -> typing.Any:
        return self.bot.database.user_settings.get(self.get_id(), setting,
            default)
    def find_settings(self, pattern: str, default: typing.Any=[]
            ) -> typing.List[typing.Any]:
        return self.bot.database.user_settings.find(self.get_id(), pattern,
            default)
    def find_settings_prefix(self, prefix: str, default: typing.Any=[]
            ) -> typing.List[typing.Any]:
        return self.bot.database.user_settings.find_prefix(self.get_id(),
            prefix, default)
    def del_setting(self, setting):
        self.bot.database.user_settings.delete(self.get_id(), setting)
    def get_channel_settings_per_setting(self, setting: str,
            default: typing.Any=[]) -> typing.List[typing.Any]:
        return self.bot.database.user_channel_settings.find_by_setting(
            self.get_id(), setting, default)

    def send_message(self, message: str, prefix: str=None, tags: dict={}):
        self.server.send_message(self.nickname, message, prefix=prefix,
            tags=tags)
    def send_notice(self, text: str, prefix: str=None, tags: dict={}):
        self.server.send_notice(self.nickname, text, prefix=prefix, tags=tags)
    def send_ctcp_response(self, command: str, args: str):
        self.send_notice("\x01%s %s\x01" % (command, args))
