import uuid
import IRCLog

class User(object):
    def __init__(self, nickname, server, bot):
        self.set_nickname(nickname)
        self.username = None
        self.hostname = None
        self.realname = None
        self.server = server
        self.bot = bot
        self.channels = set([])
        self.log = IRCLog.Log(bot)
    def set_nickname(self, nickname):
        self.nickname = nickname
        self.nickname_lower = nickname.lower()
        self.name = self.nickname_lower
    def join_channel(self, channel):
        self.channels.add(channel)
    def part_channel(self, channel):
        self.channels.remove(channel)
    def set_setting(self, setting, value):
        self.bot.database.set_user_setting(self.server.id, self.nickname,
            setting, value)
    def get_setting(self, setting, default=None):
        return self.bot.database.get_user_setting(self.server.id,
            self.nickname, setting, default)
    def find_settings(self, pattern, default=[]):
        return self.bot.database.find_user_settings(self.server.id,
            self.nickname, pattern, default)
    def find_settings_prefix(self, prefix, default=[]):
        return self.bot.database.find_user_settings_prefix(
            self.server.id, self.nickname, prefix, default)
    def del_setting(self, setting):
        self.bot.database.del_user_setting(self.server.id, self.nickname,
            setting)

    def send_message(self, message, prefix=None):
        self.server.send_message(self.nickname, message, prefix=prefix)
    def send_notice(self, message):
        self.server.send_notice(self.nickname, message)
    def send_ctcp_response(self, command, args):
        self.send_notice("\x01%s %s\x01" % (command, args))
