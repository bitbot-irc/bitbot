import uuid
from . import IRCBuffer, Utils

class User(object):
    def __init__(self, nickname, id, server, bot):
        self.server = server
        self.set_nickname(nickname)
        self._id = id
        self.username = None
        self.hostname = None
        self.realname = None
        self.bot = bot
        self.channels = set([])

        self.identified_account = None
        self.identified_account_override = None

        self.identified_account_id = None
        self.identified_account_id_override = None
        self.away = False
        self.buffer = IRCBuffer.Buffer(bot, server)

    def __repr__(self):
        return "IRCUser.User(%s|%s)" % (self.server.name, self.name)

    def get_id(self):
        return (self.identified_account_id_override or
            self.identified_account_id or self._id)
    def get_identified_account(self):
        return (self.identified_account_override or self.identified_account)

    def set_nickname(self, nickname):
        self.nickname = nickname
        self.nickname_lower = Utils.irc_lower(self.server, nickname)
        self.name = self.nickname_lower
    def join_channel(self, channel):
        self.channels.add(channel)
    def part_channel(self, channel):
        self.channels.remove(channel)
    def set_setting(self, setting, value):
        self.bot.database.user_settings.set(self.get_id(), setting, value)
    def get_setting(self, setting, default=None):
        return self.bot.database.user_settings.get(self.get_id(), setting,
            default)
    def find_settings(self, pattern, default=[]):
        return self.bot.database.user_settings.find(self.get_id(), pattern,
            default)
    def find_settings_prefix(self, prefix, default=[]):
        return self.bot.database.user_settings.find_prefix(self.get_id(),
            prefix, default)
    def del_setting(self, setting):
        self.bot.database.user_settings.delete(self.get_id(), setting)
    def get_channel_settings_per_setting(self, setting, default=[]):
        return self.bot.database.user_channel_settings.find_by_setting(
            self.get_id(), setting, default)

    def send_message(self, message, prefix=None):
        self.server.send_message(self.nickname, message, prefix=prefix)
    def send_notice(self, message):
        self.server.send_notice(self.nickname, message)
    def send_ctcp_response(self, command, args):
        self.send_notice("\x01%s %s\x01" % (command, args))
