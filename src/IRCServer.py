import collections, datetime, socket, ssl, sys, time, typing
from src import EventManager, IRCBot, IRCChannel, IRCChannels, IRCLine
from src import IRCObject, IRCUser, utils

THROTTLE_LINES = 4
THROTTLE_SECONDS = 1
UNTHROTTLED_MAX_LINES = 10

READ_TIMEOUT_SECONDS = 120
PING_INTERVAL_SECONDS = 30

class Server(IRCObject.Object):
    def __init__(self,
            bot: "IRCBot.Bot",
            events: EventManager.EventHook,
            id: int,
            alias: typing.Optional[str],
            connection_params: utils.irc.IRCConnectionParameters):
        self.connected = False
        self.bot = bot
        self.events = events
        self.id = id
        self.alias = alias
        self.connection_params = connection_params
        self.name = None # type: typing.Optional[str]

        self.nickname = None # type: typing.Optional[str]
        self.username = None # type: typing.Optional[str]
        self.realname = None # type: typing.Optional[str]
        self.hostname = None # type: typing.Optional[str]

        self._capability_queue = set([]) # type: typing.Set[str]
        self._capabilities_waiting = set([]) # type: typing.Set[str]
        self.capabilities = set([]) # type: typing.Set[str]
        self.requested_capabilities = [] # type: typing.List[str]
        self.server_capabilities = {} # type: typing.Dict[str, str]
        self.batches = {} # type: typing.Dict[str, utils.irc.IRCParsedLine]
        self.cap_started = False

        self.write_buffer = b""
        self.queued_lines = [] # type: typing.List[IRCLine.Line]
        self.buffered_lines = [] # type: typing.List[IRCLine.Line]
        self._write_throttling = False
        self.read_buffer = b""
        self.recent_sends = [] # type: typing.List[float]
        self.cached_fileno = None # type: typing.Optional[int]
        self.bytes_written = 0
        self.bytes_read = 0

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
        self.channel_paramatered_modes = ["k"] # type: typing.List[str]
        self.channel_setting_modes = ["l"] # type: typing.List[str]
        self.channel_modes = [
            "n", "i", "m", "t", "p", "s"
        ] # type: typing.List[str]

        self.channel_types = ["#"]
        self.case_mapping = "rfc1459"

        self.motd_lines = [] # type: typing.List[str]
        self.motd_done = False

        self.last_read = time.monotonic()
        self.last_send = None # type: typing.Optional[float]

        self.attempted_join = {} # type: typing.Dict[str, typing.Optional[str]]
        self.ping_sent = False

        self.events.on("timer.rejoin").hook(self.try_rejoin)

    def __repr__(self) -> str:
        return "IRCServer.Server(%s)" % self.__str__()
    def __str__(self) -> str:
        if self.alias:
            return self.alias
        return "%s:%s%s" % (self.connection_params.hostname,
            "+" if self.connection_params.tls else "",
            self.connection_params.port)
    def fileno(self) -> int:
        return self.cached_fileno or self.socket.fileno()

    def hostmask(self):
        return "%s!%s@%s" % (self.nickname, self.username, self.hostname)

    def tls_wrap(self):
        client_certificate = self.bot.config.get("tls-certificate", None)
        client_key = self.bot.config.get("tls-key", None)
        verify = self.get_setting("ssl-verify", True)

        server_hostname = None
        if not utils.is_ip(self.connection_params.hostname):
            server_hostname = self.connection_params.hostname

        self.socket = utils.security.ssl_wrap(self.socket,
            cert=client_certificate, key=client_key,
            verify=verify, hostname=server_hostname)

    def connect(self):
        ipv4 = self.connection_params.ipv4
        family = socket.AF_INET if ipv4 else socket.AF_INET6
        self.socket = socket.socket(family, socket.SOCK_STREAM)

        self.socket.settimeout(5.0)

        if self.connection_params.bindhost:
            self.socket.bind((self.connection_params.bindhost, 0))
        if self.connection_params.tls:
            self.tls_wrap()

        self.socket.connect((self.connection_params.hostname,
            self.connection_params.port))
        self.cached_fileno = self.socket.fileno()

        if self.connection_params.password:
            self.send_pass(self.connection_params.password)

        self.send_capibility_ls()

        nickname = self.connection_params.nickname
        username = self.connection_params.username or nickname
        realname = self.connection_params.realname or nickname

        self.send_user(username, realname)
        self.send_nick(nickname)
        self.connected = True
    def disconnect(self):
        self.connected = False
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except:
            pass
        try:
            self.socket.close()
        except:
            pass

    def set_setting(self, setting: str, value: typing.Any):
        self.bot.database.server_settings.set(self.id, setting,
            value)
    def get_setting(self, setting: str, default: typing.Any=None
            ) -> typing.Any:
        return self.bot.database.server_settings.get(self.id,
            setting, default)
    def find_settings(self, pattern: str, default: typing.Any=[]
            ) -> typing.List[typing.Any]:
        return self.bot.database.server_settings.find(self.id,
            pattern, default)
    def find_settings_prefix(self, prefix: str, default: typing.Any=[]
            ) -> typing.List[typing.Any]:
        return self.bot.database.server_settings.find_prefix(
            self.id, prefix, default)
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
    def get_user(self, nickname: str, create: bool=True
            ) -> typing.Optional[IRCUser.User]:
        if not self.has_user(nickname) and create:
            user_id = self.get_user_id(nickname)
            new_user = IRCUser.User(nickname, user_id, self, self.bot)
            self.events.on("new.user").call(user=new_user, server=self)
            self.users[new_user.nickname_lower] = new_user
            self.new_users.add(new_user)
        return self.users.get(self.irc_lower(nickname),
            None)
    def get_user_id(self, nickname: str) -> int:
        nickname_lower = self.irc_lower(nickname)
        self.bot.database.users.add(self.id, nickname_lower)
        return self.bot.database.users.get_id(self.id, nickname_lower)
    def remove_user(self, user: IRCUser.User):
        del self.users[user.nickname_lower]
        for channel in user.channels:
            channel.remove_user(user)

    def get_target(self, name: str
            ) -> typing.Optional[
            typing.Union[IRCChannel.Channel, IRCUser.User]]:
        if name[0] in self.channel_types:
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

    def parse_data(self, line: str):
        if not line:
            return

        self.bot.log.debug("%s (raw recv) | %s", [str(self), line])
        self.events.on("raw.received").call_unsafe(server=self, line=line)
        self.check_users()
    def check_users(self):
        for user in self.new_users:
            if not len(user.channels):
                self.remove_user(user)
        self.new_users.clear()
    def read(self) -> typing.Optional[typing.List[str]]:
        data = b""
        try:
            data = self.socket.recv(4096)
        except (ConnectionResetError, socket.timeout, OSError):
            self.disconnect()
            return None
        if not data:
            self.disconnect()
            return None
        self.bytes_read += len(data)
        data = self.read_buffer+data
        self.read_buffer = b""

        data_lines = [line.strip(b"\r") for line in data.split(b"\n")]
        if data_lines[-1]:
            self.read_buffer = data_lines[-1]
            self.bot.log.trace("recevied and buffered non-complete line: %s",
                [data_lines[-1]])

        data_lines.pop(-1)
        decoded_lines = []

        for line in data_lines:
            encoding = self.get_setting("encoding", "utf8")
            try:
                decoded_line = line.decode(encoding)
            except:
                self.bot.log.trace("can't decode line with '%s', falling back",
                    [encoding])
                try:
                    decoded_line = line.decode(self.get_setting(
                        "fallback-encoding", "latin-1"))
                except:
                    continue
            decoded_lines.append(decoded_line)

        self.last_read = time.monotonic()
        self.ping_sent = False
        return decoded_lines

    def until_next_ping(self) -> typing.Optional[float]:
        if self.ping_sent:
            return None
        return max(0, (self.last_read+PING_INTERVAL_SECONDS
            )-time.monotonic())
    def ping_due(self) -> bool:
        return self.until_next_ping() == 0

    def until_read_timeout(self) -> float:
        return max(0, (self.last_read+READ_TIMEOUT_SECONDS
            )-time.monotonic())
    def read_timed_out(self) -> bool:
        return self.until_read_timeout == 0

    def send(self, line: str):
        results = self.events.on("preprocess.send").call_unsafe(
            server=self, line=line)
        for result in results:
            if result:
                line = result
                break

        line_stripped = line.split("\n", 1)[0].strip("\r")
        line_obj = IRCLine.Line(self, datetime.datetime.utcnow(), line_stripped)
        self.queued_lines.append(line_obj)

        return line_obj

    def _send(self):
        if not len(self.write_buffer):
            throttle_space = self.throttle_space()
            to_buffer = self.queued_lines[:throttle_space]
            self.queued_lines = self.queued_lines[throttle_space:]
            for line in to_buffer:
                decoded_data = line.decoded_data()
                self.bot.log.debug("%s (raw send) | %s",
                    [str(self), decoded_data])
                self.events.on("raw.send").call_unsafe(
                    server=self, line=decoded_data)

                self.write_buffer += line.data()
                self.buffered_lines.append(line)

        bytes_written_i = self.socket.send(self.write_buffer)
        bytes_written = self.write_buffer[:bytes_written_i]
        lines_sent = bytes_written.count(b"\r\n")
        for i in range(lines_sent):
            self.buffered_lines.pop(0).sent()

        self.write_buffer = self.write_buffer[bytes_written_i:]

        self.bytes_written += bytes_written_i

        if not self.waiting_send():
            self.events.on("writebuffer.empty").call(server=self)

        now = time.monotonic()
        self.recent_sends.append(now)
        self.last_send = now
    def waiting_send(self) -> bool:
        return bool(len(self.write_buffer)) or bool(len(self.queued_lines))

    def throttle_done(self) -> bool:
        return self.send_throttle_timeout() == 0

    def throttle_prune(self):
        now = time.monotonic()
        popped = 0
        for i, recent_send in enumerate(self.recent_sends[:]):
            time_since = now-recent_send
            if time_since >= THROTTLE_SECONDS:
                self.recent_sends.pop(i-popped)
                popped += 1

    def throttle_space(self) -> int:
        if not self._write_throttling:
            return UNTHROTTLED_MAX_LINES
        return max(0, THROTTLE_LINES-len(self.recent_sends))

    def send_throttle_timeout(self) -> float:
        if len(self.write_buffer) or not self._write_throttling:
            return 0

        self.throttle_prune()
        if self.throttle_space() > 0:
            return 0

        time_left = self.recent_sends[0]+THROTTLE_SECONDS
        time_left = time_left-time.monotonic()
        return time_left

    def set_write_throttling(self, is_on: bool):
        self._write_throttling = is_on

    def send_user(self, username: str, realname: str) -> IRCLine.Line:
        return self.send("USER %s 0 * :%s" % (username, realname))
    def send_nick(self, nickname: str) -> IRCLine.Line:
        return self.send("NICK %s" % nickname)

    def send_capibility_ls(self) -> IRCLine.Line:
        return self.send("CAP LS 302")
    def queue_capability(self, capability: str):
        self._capability_queue.add(capability)
    def queue_capabilities(self, capabilities: typing.List[str]):
        self._capability_queue.update(capabilities)
    def send_capability_queue(self):
        if self.has_capability_queue():
            capabilities = " ".join(self._capability_queue)
            self.requested_capabilities = list(self._capability_queue)
            self._capability_queue.clear()
            self.send_capability_request(capabilities)
    def has_capability_queue(self):
        return bool(len(self._capability_queue))
    def send_capability_request(self, capability: str) -> IRCLine.Line:
        return self.send("CAP REQ :%s" % capability)
    def send_capability_end(self) -> IRCLine.Line:
        return self.send("CAP END")
    def send_authenticate(self, text: str) -> IRCLine.Line:
        return self.send("AUTHENTICATE %s" % text)

    def waiting_for_capabilities(self) -> bool:
        return bool(len(self._capabilities_waiting))
    def wait_for_capability(self, capability: str):
        self._capabilities_waiting.add(capability)
    def capability_done(self, capability: str):
        self._capabilities_waiting.discard(capability)
        if self.cap_started and not self._capabilities_waiting:
            self.send_capability_end()

    def send_pass(self, password: str) -> IRCLine.Line:
        return self.send("PASS %s" % password)

    def send_ping(self, nonce: str="hello") -> IRCLine.Line:
        return self.send("PING :%s" % nonce)
    def send_pong(self, nonce: str="hello") -> IRCLine.Line:
        return self.send("PONG :%s" % nonce)

    def try_rejoin(self, event: EventManager.Event):
        if event["server_id"] == self.id and event["channel_name"
                ] in self.attempted_join:
            self.send_join(event["channel_name"], event["key"])
    def send_join(self, channel_name: str, key: str=None) -> IRCLine.Line:
        return self.send("JOIN %s%s" % (channel_name,
            "" if key else " %s" % key))
    def send_part(self, channel_name: str, reason: str=None) -> IRCLine.Line:
        return self.send("PART %s%s" % (channel_name,
            "" if reason == None else " %s" % reason))
    def send_quit(self, reason: str="Leaving") -> IRCLine.Line:
        return self.send("QUIT :%s" % reason)

    def _tag_str(self, tags: dict) -> str:
        tag_str = ""
        for tag, value in tags.items():
            if tag_str:
                tag_str += ","
            tag_str += tag
            if value:
                tag_str += "=%s" % value
        if tag_str:
            tag_str = "@%s " % tag_str
        return tag_str

    def send_message(self, target: str, message: str, prefix: str=None,
            tags: dict={}) -> IRCLine.Line:
        full_message = message if not prefix else prefix+message
        return self.send("%sPRIVMSG %s :%s" % (self._tag_str(tags), target,
            full_message))

    def send_notice(self, target: str, message: str, prefix: str=None,
            tags: dict={}) -> IRCLine.Line:
        full_message = message if not prefix else prefix+message
        return self.send("%sNOTICE %s :%s" % (self._tag_str(tags), target,
            full_message))

    def send_mode(self, target: str, mode: str=None, args: str=None
            ) -> IRCLine.Line:
        return self.send("MODE %s%s%s" % (target,
            "" if mode == None else " %s" % mode,
            "" if args == None else " %s" % args))

    def send_topic(self, channel_name: str, topic: str) -> IRCLine.Line:
        return self.send("TOPIC %s :%s" % (channel_name, topic))
    def send_kick(self, channel_name: str, target: str, reason: str=None
            ) -> IRCLine.Line:
        return self.send("KICK %s %s%s" % (channel_name, target,
            "" if reason == None else " :%s" % reason))
    def send_names(self, channel_name: str) -> IRCLine.Line:
        return self.send("NAMES %s" % channel_name)
    def send_list(self, search_for: str=None) -> IRCLine.Line:
        return self.send(
            "LIST%s" % "" if search_for == None else " %s" % search_for)
    def send_invite(self, target: str, channel_name: str) -> IRCLine.Line:
        return self.send("INVITE %s %s" % (target, channel_name))

    def send_whois(self, target: str) -> IRCLine.Line:
        return self.send("WHOIS %s" % target)
    def send_whowas(self, target: str, amount: int=None, server: str=None
            ) -> IRCLine.Line:
        return self.send("WHOWAS %s%s%s" % (target,
            "" if amount == None else " %s" % amount,
            "" if server == None else " :%s" % server))
    def send_who(self, filter: str=None) -> IRCLine.Line:
        return self.send("WHO%s" % ("" if filter == None else " %s" % filter))
    def send_whox(self, mask: str, filter: str, fields: str, label: str=None
            ) -> IRCLine.Line:
        return self.send("WHO %s %s%%%s%s" % (mask, filter, fields,
            ","+label if label else ""))
