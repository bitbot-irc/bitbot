import IRCLog

class Channel(object):
    def __init__(self, name, server, bot):
        self.name = name.lower()
        self.server = server
        self.bot = bot
        self.topic = ""
        self.topic_setter_nickname = None
        self.topic_setter_username = None
        self.topic_setter_hostname = None
        self.topic_time = 0
        self.users = set([])
        self.modes = {}
        self.created_timestamp = None
        self.log = IRCLog.Log(bot)
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
    def has_user(self, user):
        return user in self.users
    def add_mode(self, mode, args=None):
        if not mode in self.modes:
            self.modes[mode] = set([])
        if args:
            self.modes[mode].add(args.lower())
        self.bot.events.on("mode").on("channel").call(
            channel=self, mode=mode, args=args, remove=False)
    def remove_mode(self, mode, args=None):
        if not args:
            del self.modes[mode]
        else:
            self.modes[mode].discard(args.lower())
            if not len(self.modes[mode]):
                del self.modes[mode]
        self.bot.events.on("mode").on("channel").call(
            channel=self, mode=mode, args=args, remove=True)
    def set_setting(self, setting, value):
        self.bot.database.set_channel_setting(self.server.id,
            self.name, setting, value)
    def get_setting(self, setting, default=None):
        return self.bot.database.get_channel_setting(
            self.server.id, self.name, setting, default)
    def find_settings(self, pattern, default=[]):
        return self.bot.database.find_channel_setting(
            self.server.id, self.name, pattern, default)
    def del_setting(self, setting):
        self.bot.database.del_channel_setting(self.server.id,
            self.name, setting)

    def send_message(self, text):
        self.server.send_message(self.name, text)
    def send_mode(self, mode=None, target=None):
        self.server.send_mode(self.name, mode, target)
    def send_kick(self, target, reason=None):
        self.server.send_kick(self.name, target, reason)
    def send_ban(self, hostmask):
        self.server.send_mode(self.name, "+b", hostmask)

    def mode_or_above(self, nickname, mode):
        mode_orders = list(self.server.mode_prefixes.values())
        mode_index = mode_orders.index(mode)
        for mode in mode_orders[:mode_index+1]:
            if nickname.lower() in self.modes.get(mode, []):
                return True
        return False
