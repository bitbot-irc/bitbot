import re, typing, uuid
from src import EventManager, IRCBot, IRCBuffer, IRCObject, IRCServer, IRCUser
from src import utils

RE_MODES = re.compile(r"[-+]\w+")

class Channel(IRCObject.Object):
    name = ""
    def __init__(self, name: str, id, server: "IRCServer.Server",
            bot: "IRCBot.Bot"):
        self.name = server.irc_lower(name)
        self.id = id
        self.server = server
        self.bot = bot
        self.topic = ""
        self.topic_setter_nickname = None # type: typing.Optional[str]
        self.topic_setter_username = None # type: typing.Optional[str]
        self.topic_setter_hostname = None # type: typing.Optional[str]
        self.topic_time = 0
        self.users = set([]) # type: typing.Set[IRCUser.User]
        self.modes = {} # type: typing.Dict[str, typing.Set]
        self.user_modes = {} # type: typing.Dict[IRCUser.User, typing.Set]
        self.created_timestamp = None
        self.buffer = IRCBuffer.Buffer(bot, server)

    def __repr__(self) -> str:
        return "IRCChannel.Channel(%s|%s)" % (self.server.name, self.name)
    def __str__(self) -> str:
        return self.name

    def set_topic(self, topic: str):
        self.topic = topic
    def set_topic_setter(self, nickname: str, username: str=None,
            hostname: str=None):
        self.topic_setter_nickname = nickname
        self.topic_setter_username = username
        self.topic_setter_hostname = hostname
    def set_topic_time(self, unix_timestamp: int):
        self.topic_time = unix_timestamp

    def add_user(self, user: IRCUser.User):
        self.users.add(user)
    def remove_user(self, user: IRCUser.User):
        self.users.remove(user)
        for mode in list(self.modes.keys()):
            if mode in self.server.prefix_modes and user in self.modes[mode]:
                self.modes[mode].discard(user)
                if not len(self.modes[mode]):
                    del self.modes[mode]
                if user in self.user_modes:
                    del self.user_modes[user]
    def has_user(self, user: IRCUser.User) -> bool:
        return user in self.users

    def mode_str(self) -> str:
        modes = [] # type: typing.List[typing.Tuple[str, typing.List[str]]]
        # sorta alphanumerically by mode char
        modes_iter = sorted(self.modes.items(), key=lambda mode: mode[0])

        for mode, args in modes_iter:
            # not list mode (e.g. +b) and not prefix mode (e.g. +o)
            if (not mode in self.server.channel_list_modes and
                    not mode in self.server.prefix_modes):
                args_list = typing.cast(typing.List[str], list(args))
                modes.append((mode, args_list))

        # move modes with args to the front
        modes.sort(key=lambda mode: not bool(mode[1]))

        out_modes = "".join(mode for mode, args in modes)
        out_args = " ".join(args[0] for mode, args in modes if args)

        return "+%s%s" % (out_modes, " %s" % out_args if out_args else "")

    def add_mode(self, mode: str, arg: str=None):
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
    def remove_mode(self, mode: str, arg: str=None):
        if not arg:
            if mode in self.modes:
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
            if mode in self.modes and not len(self.modes[mode]):
                del self.modes[mode]
    def change_mode(self, remove: bool, mode: str, arg: str=None):
        if remove:
            self.remove_mode(mode, arg)
        else:
            self.add_mode(mode, arg)

    def parse_modes(self, modes: str, args: typing.List[str]
            ) -> typing.List[typing.Tuple[str, typing.Optional[str]]]:
        new_modes: typing.List[typing.Tuple[str, typing.Optional[str]]] = []
        for chunk in RE_MODES.findall(modes):
            remove = chunk[0] == "-"
            for mode in chunk[1:]:
                new_arg = None
                if mode in self.server.channel_list_modes:
                    new_arg = args.pop(0)
                elif (mode in self.server.channel_parametered_modes or
                        mode in self.server.prefix_modes):
                    new_arg = args.pop(0)
                    self.change_mode(remove, mode, new_arg)
                elif mode in self.server.channel_setting_modes:
                    if remove:
                        self.change_mode(remove, mode)
                    else:
                        new_arg = args.pop(0)
                        self.change_mode(remove, mode, new_arg)
                elif mode in self.server.channel_modes:
                    self.change_mode(remove, mode)

                mode_str = "%s%s" % ("-" if remove else "+", mode)
                new_modes.append((mode_str, new_arg))
        return new_modes

    def set_setting(self, setting: str, value: typing.Any):
        self.bot.database.channel_settings.set(self.id, setting, value)
    def get_setting(self, setting: str, default: typing.Any=None
            ) -> typing.Any:
        return self.bot.database.channel_settings.get(self.id, setting,
            default)
    def find_settings(self, pattern: str, default: typing.Any=[]
            ) -> typing.List[typing.Any]:
        return self.bot.database.channel_settings.find(self.id, pattern,
            default)
    def find_settings_prefix(self, prefix: str, default: typing.Any=[]
            ) -> typing.List[typing.Any]:
        return self.bot.database.channel_settings.find_prefix(self.id,
            prefix, default)
    def del_setting(self, setting: str):
        self.bot.database.channel_settings.delete(self.id, setting)

    def set_user_setting(self, user_id: int, setting: str, value: typing.Any):
        self.bot.database.user_channel_settings.set(user_id, self.id,
            setting, value)
    def get_user_setting(self, user_id: int, setting: str,
            default: typing.Any=None) -> typing.Any:
        return self.bot.database.user_channel_settings.get(user_id,
            self.id, setting, default)
    def find_user_settings(self, user_id: int, pattern: str,
            default: typing.Any=[]) -> typing.List[typing.Any]:
        return self.bot.database.user_channel_settings.find(user_id,
            self.id, pattern, default)
    def find_user_settings_prefix(self, user_id: int, prefix: str,
            default: typing.Any=[]) -> typing.List[typing.Any]:
        return self.bot.database.user_channel_settings.find_prefix(
            user_id, self.id, prefix, default)
    def del_user_setting(self, user_id: int, setting: str):
        self.bot.database.user_channel_settings.delete(user_id, self.id,
            setting)
    def find_all_by_setting(self, setting: str, default: typing.Any=[]
            ) -> typing.List[typing.Any]:
        return self.bot.database.user_channel_settings.find_all_by_setting(
            self.id, setting, default)

    def send_message(self, text: str, tags: dict={}):
        return self.server.send_message(self.name, text, tags=tags)
    def send_notice(self, text: str, tags: dict={}):
        return self.server.send_notice(self.name, text, tags=tags)
    def send_tagmsg(self, tags: dict):
        return self.server.send_tagmsg(self.name, tags)

    def send_mode(self, mode: str=None, target: typing.List[str]=None):
        return self.server.send_mode(self.name, mode, target)
    def send_kick(self, target: str, reason: str=None):
        return self.server.send_kick(self.name, target, reason)
    def send_ban(self, hostmask: str):
        return self.server.send_mode(self.name, "+b", [hostmask])
    def send_unban(self, hostmask: str):
        return self.server.send_mode(self.name, "-b", [hostmask])
    def send_topic(self, topic: str):
        return self.server.send_topic(self.name, topic)
    def send_part(self, reason: str=None):
        return self.server.send_part(self.name, reason)

    def mode_or_above(self, user: IRCUser.User, mode: str) -> bool:
        mode_orders = list(self.server.prefix_modes)
        mode_index = mode_orders.index(mode)
        for mode in mode_orders[:mode_index+1]:
            if user in self.modes.get(mode, []):
                return True
        return False

    def has_mode(self, user: IRCUser.User, mode: str) -> bool:
        return user in self.modes.get(mode, [])

    def get_user_status(self, user: IRCUser.User) -> typing.Set:
        return self.user_modes.get(user, set([]))
