import collections, datetime, sys, time, typing
from src import EventManager, IRCBot, IRCChannel, IRCChannels, IRCLine
from src import IRCObject, IRCSocket, IRCUser, utils

READ_TIMEOUT_SECONDS = 120
PING_INTERVAL_SECONDS = 30

class Server(IRCObject.Object):
    def __init__(self,
            bot: "IRCBot.Bot",
            events: EventManager.Events,
            id: int,
            alias: str,
            connection_params: utils.irc.IRCConnectionParameters):
        self.bot = bot
        self.events = events
        self.id = id
        self.alias = alias
        self.connection_params = connection_params
        self.name = None # type: typing.Optional[str]
        self.version = None # type: typing.Optional[str]

        self.connected = False
        self.reconnected = False
        self.from_init = False

        self.nickname = None # type: typing.Optional[str]
        self.username = None # type: typing.Optional[str]
        self.realname = None # type: typing.Optional[str]
        self.hostname = None # type: typing.Optional[str]

        self.capability_queue = {
            } # type: typing.Dict[str, utils.irc.Capability]
        self.capabilities_requested = {
            } # type: typing.Dict[str, utils.irc.Capability]

        self._capabilities_waiting = set([]) # type: typing.Set[str]
        self.agreed_capabilities = set([]) # type: typing.Set[str]
        self.server_capabilities = {} # type: typing.Dict[str, str]
        self.batches = {} # type: typing.Dict[str, utils.irc.IRCBatch]

        self.users = {} # type: typing.Dict[str, IRCUser.User]
        self.new_users = set([]) #type: typing.Set[IRCUser.User]
        self.channels = IRCChannels.Channels(self, self.bot, self.events)
        self.own_modes = {} # type: typing.Dict[str, typing.Optional[str]]

        self.isupport = {} # type: typing.Dict[str, typing.Optional[str]]

        self.prefix_symbols = collections.OrderedDict(
            (("@", "o"), ("+", "v")))
        self.prefix_modes = collections.OrderedDict(
            (("o", "@"), ("v", "+")))

        self.channel_list_modes = ["b"] # type: typing.List[str]
        self.channel_parametered_modes = ["k"] # type: typing.List[str]
        self.channel_setting_modes = ["l"] # type: typing.List[str]
        self.channel_modes = [
            "n", "i", "m", "t", "p", "s"
        ] # type: typing.List[str]

        self.channel_types = ["#"]
        self.case_mapping = "rfc1459"
        self.statusmsg = [] # type: typing.List[str]

        self.motd_lines = [] # type: typing.List[str]
        self.motd_done = False

        self.ping_sent = False
        self.send_enabled = True

    def __repr__(self) -> str:
        return "IRCServer.Server(%s)" % self.__str__()
    def __str__(self) -> str:
        return self.alias

    def fileno(self) -> int:
        return self.socket.fileno()

    def hostmask(self):
        return "%s!%s@%s" % (self.nickname, self.username, self.hostname)

    def connect(self):
        self.socket = IRCSocket.Socket(
            self.bot.log,
            self.get_setting("encoding", "utf8"),
            self.get_setting("fallback-encoding", "iso-8859-1"),
            self.connection_params.hostname,
            self.connection_params.port,
            self.connection_params.bindhost,
            self.connection_params.tls,
            tls_verify=self.get_setting("ssl-verify", True),
            cert=self.bot.config.get("tls-certificate", None),
            key=self.bot.config.get("tls-key", None))
        self.events.on("preprocess.connect").call(server=self)
        self.socket.connect()

        if self.connection_params.password:
            self.send_pass(self.connection_params.password)

        self.send_capibility_ls()

        nickname = self.connection_params.nickname
        username = self.connection_params.username or nickname
        realname = self.connection_params.realname or nickname

        self.send_user(username, realname)
        self.send_nick(nickname)

    def disconnect(self):
        self.socket.disconnect()

    def set_setting(self, setting: str, value: typing.Any):
        self.bot.database.server_settings.set(self.id, setting,
            value)
    def get_setting(self, setting: str, default: typing.Any=None
            ) -> typing.Any:
        return self.bot.database.server_settings.get(self.id,
            setting, default)
    def find_settings(self, pattern: str=None, prefix: str=None,
            default: typing.Any=[]) -> typing.List[typing.Any]:
        if not pattern == None:
            return self.bot.database.server_settings.find(self.id, pattern,
                default)
        elif not prefix == None:
            return self.bot.database.server_settings.find_prefix(self.id,
                prefix, default)
        else:
            raise ValueError("Please provide 'pattern' or 'prefix'")
    def del_setting(self, setting: str):
        self.bot.database.server_settings.delete(self.id, setting)

    def get_user_setting(self, nickname: str, setting: str,
            default: typing.Any=None) -> typing.Any:
        user_id = self.get_user_id(nickname)
        return self.bot.database.user_settings.get(user_id, setting, default)
    def set_user_setting(self, nickname: str, setting: str, value: typing.Any):
        user_id = self.get_user_id(nickname)
        self.bot.database.user_settings.set(user_id, setting, value)

    def get_all_user_settings(self, setting: str, default: typing.Any=[]
            ) -> typing.List[typing.Any]:
        return self.bot.database.user_settings.find_all_by_setting(
            self.id, setting, default)
    def find_all_user_channel_settings(self, setting: str,
            default: typing.Any=[]) -> typing.List[typing.Any]:
        return self.bot.database.user_channel_settings.find_all_by_setting(
            self.id, setting, default)

    def set_own_nickname(self, nickname: str):
        self.nickname = nickname
        self.nickname_lower = self.irc_lower(nickname)
    def is_own_nickname(self, nickname: str) -> bool:
        if self.nickname == None:
            return False
        return self.irc_equals(nickname, typing.cast(str, self.nickname))

    def add_own_mode(self, mode: str, arg: str=None):
        self.own_modes[mode] = arg
    def remove_own_mode(self, mode: str):
        del self.own_modes[mode]
    def change_own_mode(self, remove: bool, mode: str, arg: str=None):
        if remove:
            self.remove_own_mode(mode)
        else:
            self.add_own_mode(mode, arg)

    def has_user(self, nickname: str) -> bool:
        return self.irc_lower(nickname) in self.users
    def get_user(self, nickname: str, username: str=None, hostname: str=None,
            create: bool=True) -> typing.Optional[IRCUser.User]:
        new = False
        if not self.has_user(nickname) and create:
            new = True
            user_id = self.get_user_id(nickname)
            new_user = IRCUser.User(nickname, user_id, self, self.bot)
            self.users[new_user.nickname_lower] = new_user
            self.new_users.add(new_user)

        user = self.users.get(self.irc_lower(nickname), None)
        if user:
            if not username == None:
                user.username = username
            if not hostname == None:
                user.hostname = hostname
        if new:
            self.events.on("new.user").call(user=new_user, server=self)
        return user

    def get_user_id(self, nickname: str) -> int:
        nickname_lower = self.irc_lower(nickname)
        self.bot.database.users.add(self.id, nickname_lower)
        return self.bot.database.users.get_id(self.id, nickname_lower)
    def has_user_id(self, nickname: str) -> bool:
        id = self.bot.database.users.get_id(self.id, self.irc_lower(nickname))
        return not id == None
    def remove_user(self, user: IRCUser.User):
        del self.users[user.nickname_lower]
        for channel in user.channels:
            channel.remove_user(user)

    def is_channel(self, name: str) -> bool:
        return name[0] in self.channel_types

    def get_target(self, name: str
            ) -> typing.Optional[
            typing.Union[IRCChannel.Channel, IRCUser.User]]:
        if self.is_channel(name):
            if name in self.channels:
                return self.channels.get(name)
        else:
            return self.get_user(name)
        return None

    def change_user_nickname(self, old_nickname: str, new_nickname: str):
        user = self.users.pop(self.irc_lower(old_nickname))
        user._id = self.get_user_id(new_nickname)
        self.users[self.irc_lower(new_nickname)] = user

    def irc_lower(self, s: str) -> str:
        return utils.irc.lower(self.case_mapping, s)
    def irc_equals(self, s1: str, s2: str) -> bool:
        return utils.irc.equals(self.case_mapping, s1, s2)

    def hostmask_match(self, hostmask: str, pattern: str) -> bool:
        return utils.irc.hostmask_match(self.irc_lower(hostmask),
            self.irc_lower(pattern))

    def _post_read(self, lines: typing.List[str]):
        for line in lines:
            self.bot.log.debug("%s (raw recv) | %s", [str(self), line])
            self.events.on("raw.received").call_unsafe(server=self,
                line=utils.irc.parse_line(line))
            self.check_users()
    def check_users(self):
        for user in self.new_users:
            if not len(user.channels):
                self.remove_user(user)
        self.new_users.clear()

    def until_next_ping(self) -> typing.Optional[float]:
        if self.ping_sent:
            return None
        return max(0, (self.socket.last_read+PING_INTERVAL_SECONDS
            )-time.monotonic())
    def ping_due(self) -> bool:
        return self.until_next_ping() == 0

    def until_read_timeout(self) -> float:
        return max(0, (self.socket.last_read+READ_TIMEOUT_SECONDS
            )-time.monotonic())
    def read_timed_out(self) -> bool:
        return self.until_read_timeout() == 0

    def read(self) -> typing.Optional[typing.List[str]]:
        lines = self.socket.read()
        if lines:
            self.ping_sent = False

        return lines

    def _send(self) -> typing.List[IRCLine.SentLine]:
        lines = self.socket._send()
        for line in lines:
            self.bot.log.debug("%s (raw send) | %s", [
                str(self), line.parsed_line.format()])
        return lines
    def _post_send(self, lines: typing.List[IRCLine.SentLine]):
        for line in lines:
            line.events.on("send").call()
            self.events.on("raw.send").call_unsafe(server=self,
                line=line.parsed_line)

    def send(self, line_parsed: IRCLine.ParsedLine, immediate: bool=False
            ) -> typing.Optional[IRCLine.SentLine]:
        if not self.send_enabled:
            return None

        line_events = self.events.new_root()

        self.events.on("preprocess.send").on(line_parsed.command
            ).call_unsafe(server=self, line=line_parsed, events=line_events)
        self.events.on("preprocess.send").call_unsafe(server=self,
            line=line_parsed, events=line_events)

        if line_parsed.valid() or line_parsed.assured():
            line = line_parsed.format()
            line_obj = IRCLine.SentLine(line_events, datetime.datetime.utcnow(),
                self.hostmask(), line_parsed)
            self.socket.send(line_obj, immediate=immediate)

            if immediate:
                self.bot.trigger_write()

            return line_obj
        return None
    def send_raw(self, line: str):
        return self.send(utils.irc.parse_line(line))

    def send_user(self, username: str, realname: str
            ) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.user(username, realname))
    def send_nick(self, nickname: str) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.nick(nickname))

    def send_capibility_ls(self) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.capability_ls())
    def send_capability_queue(self):
        capability_queue = list(self.capability_queue.keys())

        for i in range(0, len(capability_queue), 10):
            capability_batch = capability_queue[i:i+10]

            for cap_name in capability_batch:
                cap = self.capability_queue[cap_name]
                del self.capability_queue[cap_name]
                self.capabilities_requested[cap_name] = cap

            self.send_capability_request(" ".join(capability_batch))

    def send_capability_request(self, capability: str
            ) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.capability_request(capability))
    def send_capability_end(self) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.capability_end())
    def send_authenticate(self, text: str) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.authenticate(text))
    def has_capability(self, capability: utils.irc.Capability) -> bool:
        return bool(self.available_capability(capability))
    def has_capability_str(self, capability: str) -> bool:
        return capability in self.agreed_capabilities
    def available_capability(self, capability: utils.irc.Capability
            ) -> typing.Optional[str]:
        return capability.available(self.agreed_capabilities)

    def waiting_for_capabilities(self) -> bool:
        return bool(len(self._capabilities_waiting))
    def wait_for_capability(self, capability: str):
        self._capabilities_waiting.add(capability)
    def capability_done(self, capability: str):
        if capability in self._capabilities_waiting:
            self._capabilities_waiting.discard(capability)
            if not self._capabilities_waiting:
                self.send_capability_end()
    def clear_waiting_capabilities(self):
        self._capabilities_waiting.clear()

    def send_pass(self, password: str) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.password(password))

    def send_ping(self, nonce: str="hello"
            ) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.ping(nonce), immediate=True)
    def send_pong(self, nonce: str) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.pong(nonce), immediate=True)

    def send_join(self, channel_name: str, keys: typing.List[str]=None
            ) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.join(channel_name, keys))
    def send_joins(self, channel_names: typing.List[str],
            keys: typing.List[str]=None):
        return self.send(utils.irc.protocol.join(",".join(channel_names),
            keys))
    def send_part(self, channel_name: str, reason: str=None
            ) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.part(channel_name, reason))
    def send_quit(self, reason: str="Leaving"
            ) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.quit(reason))

    def send_message(self, target: str, message: str, tags: dict={}
            ) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.privmsg(target, message, tags))

    def send_notice(self, target: str, message: str, tags: dict={}
            ) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.notice(target, message, tags))

    def send_tagmsg(self, target: str, tags: dict):
        return self.send(utils.irc.protocol.tagmsg(target, tags))

    def send_mode(self, target: str, mode: str=None, args: typing.List[str]=None
            ) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.mode(target, mode, args))

    def send_topic(self, channel_name: str, topic: str
            ) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.topic(channel_name, topic))
    def send_kick(self, channel_name: str, target: str, reason: str=None
            ) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.kick(channel_name, target, reason))
    def send_names(self, channel_name: str) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.names(channel_name))
    def send_list(self, search_for: str=None
            ) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.list(search_for))
    def send_invite(self, channel_name: str, target: str
            ) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.invite(channel_name, target))

    def send_whois(self, target: str) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.whois(target))
    def send_whowas(self, target: str, amount: int=None, server: str=None
            ) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.whowas(target, amount, server))
    def send_who(self, filter: str=None) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.who(filter))
    def send_whox(self, mask: str, filter: str, fields: str, label: str=None
            ) -> typing.Optional[IRCLine.SentLine]:
        return self.send(utils.irc.protocol.whox(mask, filter, fields, label))
