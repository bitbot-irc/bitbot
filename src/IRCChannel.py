import uuid
from src import IRCBuffer, IRCObject, utils

class Channel(IRCObject.Object):
    def __init__(self, name, id, server, bot):
        self.name = utils.irc.lower(server, name)
        self.id = id
        self.server = server
        self.bot = bot
        self.topic = ""
        self.topic_setter_nickname = None
        self.topic_setter_username = None
        self.topic_setter_hostname = None
        self.topic_time = 0
        self.users = set([])
        self.modes = {}
        self.user_modes = {}
        self.created_timestamp = None
        self.buffer = IRCBuffer.Buffer(bot, server)

    def __repr__(self):
        return "IRCChannel.Channel(%s|%s)" % (self.server.name, self.name)
    def __str__(self):
        return self.name

    def set_topic(self, topic):
        self.topic = topic
    def set_topic_setter(self, nickname, username=None, hostname=None):
        self.topic_setter_nickname = nickname
        self.topic_setter_username = username
        self.topic_setter_hostname = hostname
    def set_topic_time(self, unix_timestamp):
        self.topic_time = unix_timestamp

    def add_user(self, user):
        self.users.add(user)
    def remove_user(self, user):
        self.users.remove(user)
        for mode in list(self.modes.keys()):
            if mode in self.server.prefix_modes and user in self.modes[mode]:
                self.modes[mode].discard(user)
                if not len(self.modes[mode]):
                    del self.modes[mode]
                if user in self.user_modes:
                    del self.user_modes[user]
    def has_user(self, user):
        return user in self.users

    def add_mode(self, mode, arg=None):
        if not mode in self.modes:
            self.modes[mode] = set([])
        if arg:
            if mode in self.server.prefix_modes:
                user = self.server.get_user(arg)
                if user:
                    self.modes[mode].add(user)
                    if not user in self.user_modes:
                        self.user_modes[user] = set([])
                    self.user_modes[user].add(mode)
            else:
                self.modes[mode].add(arg.lower())
    def remove_mode(self, mode, arg=None):
        if not arg:
            del self.modes[mode]
        else:
            if mode in self.server.prefix_modes:
                user = self.server.get_user(arg)
                if user:
                    if mode in self.modes:
                        self.modes[mode].discard(user)
                    if user in self.user_modes:
                        self.user_modes[user].discard(mode)
                        if not self.user_modes[user]:
                            del self.user_modes[user]
            else:
                self.modes[mode].discard(arg.lower())
            if not len(self.modes[mode]):
                del self.modes[mode]
    def change_mode(self, remove, mode, arg=None):
        if remove:
            self.remove_mode(mode, arg)
        else:
            self.add_mode(mode, arg)

    def set_setting(self, setting, value):
        self.bot.database.channel_settings.set(self.id, setting, value)
    def get_setting(self, setting, default=None):
        return self.bot.database.channel_settings.get(self.id, setting,
            default)
    def find_settings(self, pattern, default=[]):
        return self.bot.database.channel_settings.find(self.id, pattern,
            default)
    def find_settings_prefix(self, prefix, default=[]):
        return self.bot.database.channel_settings.find_prefix(self.id,
            prefix, default)
    def del_setting(self, setting):
        self.bot.database.channel_settings.delete(self.id, setting)

    def set_user_setting(self, user_id, setting, value):
        self.bot.database.user_channel_settings.set(user_id, self.id,
            setting, value)
    def get_user_setting(self, user_id, setting, default=None):
        return self.bot.database.user_channel_settings.get(user_id,
            self.id, setting, default)
    def find_user_settings(self, user_i, pattern, default=[]):
        return self.bot.database.user_channel_settings.find(user_id,
            self.id, pattern, default)
    def find_user_settings_prefix(self, user_id, prefix, default=[]):
        return self.bot.database.user_channel_settings.find_prefix(
            user_id, self.id, prefix, default)
    def del_user_setting(self, user_id, setting):
        self.bot.database.user_channel_settings.delete(user_id, self.id,
            setting)
    def find_all_by_setting(self, setting, default=[]):
        return self.bot.database.user_channel_settings.find_all_by_setting(
            self.id, setting, default)

    def send_message(self, text, prefix=None, tags={}):
        self.server.send_message(self.name, text, prefix=prefix, tags=tags)
    def send_notice(self, text, prefix=None, tags={}):
        self.server.send_notice(self.name, text, prefix=prefix, tags=tags)
    def send_mode(self, mode=None, target=None):
        self.server.send_mode(self.name, mode, target)
    def send_kick(self, target, reason=None):
        self.server.send_kick(self.name, target, reason)
    def send_ban(self, hostmask):
        self.server.send_mode(self.name, "+b", hostmask)
    def send_unban(self, hostmask):
        self.server.send_mode(self.name, "-b", hostmask)
    def send_topic(self, topic):
        self.server.send_topic(self.name, topic)
    def send_part(self, reason=None):
        self.server.send_part(self.name, reason)

    def mode_or_above(self, user, mode):
        mode_orders = list(self.server.prefix_modes)
        mode_index = mode_orders.index(mode)
        for mode in mode_orders[:mode_index+1]:
            if user in self.modes.get(mode, []):
                return True
        return False

    def has_mode(self, user, mode):
        return user in self.modes.get(mode, [])

    def get_user_status(self, user):
        return self.user_modes.get(user, [])
