import collections, socket, ssl, sys, time, typing
from src import EventManager, IRCBot, IRCChannels, IRCObject, IRCUser, utils

THROTTLE_LINES = 4
THROTTLE_SECONDS = 1
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

        self._capability_queue = set([]) # type: typing.Set[str]
        self._capabilities_waiting = set([]) # type: typing.Set[str]
        self.capabilities = set([]) # type: typing.Set[str]
        self.server_capabilities = {} # type: typing.Dict[str, str]
        self.batches = {} # type: typing.Dict[str, utils.irc.IRCLine]
        self.cap_started = False

        self.write_buffer = b""
        self.buffered_lines = [] # type: typing.List[bytes]
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
        self.channel_modes = [] # type: typing.List[str]
        self.channel_types = ["#"]
        self.case_mapping = "rfc1459"

        self.motd_lines = [] # type: typing.List[str]
        self.motd_done = False

        self.last_read = time.monotonic()
        self.last_send = None # type: typing.Optional[float]

        self.attempted_join = {} # type: typing.Dict[str, typing.Optional[str]]
        self.ping_sent = False

        self.events.on("timer.rejoin").hook(self.try_rejoin)

    def __repr__(self):
        return "IRCServer.Server(%s)" % self.__str__()
    def __str__(self):
        if self.alias:
            return self.alias
        return "%s:%s%s" % (self.connection_params.hostname,
            "+" if self.connection_params.tls else "",
            self.connection_params.port)
    def fileno(self):
        return self.cached_fileno or self.socket.fileno()

    def tls_wrap(self):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1

        context.load_default_certs()
        if self.get_setting("ssl-verify", True):
            context.verify_mode = ssl.CERT_REQUIRED

        client_certificate = self.bot.config.get("tls-certificate", None)
        client_key = self.bot.config.get("tls-key", None)
        if client_certificate and client_key:
            context.load_cert_chain(client_certificate, keyfile=client_key)

        self.socket = context.wrap_socket(self.socket)

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
        self.send_capibility_ls()

        if self.connection_params.password:
            self.send_pass(self.connection_params.password)

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
    def get_setting(self, setting: str, default: typing.Any=None):
        return self.bot.database.server_settings.get(self.id,
            setting, default)
    def find_settings(self, pattern: str, default: typing.Any=[]):
        return self.bot.database.server_settings.find(self.id,
            pattern, default)
    def find_settings_prefix(self, prefix: str, default: typing.Any=[]):
        return self.bot.database.server_settings.find_prefix(
            self.id, prefix, default)
    def del_setting(self, setting: str):
        self.bot.database.server_settings.delete(self.id, setting)

    def get_user_setting(self, nickname: str, setting: str,
            default: typing.Any=None):
        user_id = self.get_user_id(nickname)
        return self.bot.database.user_settings.get(user_id, setting, default)
    def set_user_setting(self, nickname: str, setting: str, value: typing.Any):
        user_id = self.get_user_id(nickname)
        self.bot.database.user_settings.set(user_id, setting, value)

    def get_all_user_settings(self, setting: str, default: typing.Any=[]):
        return self.bot.database.user_settings.find_all_by_setting(
            self.id, setting, default)
    def find_all_user_channel_settings(self, setting: str,
            default: typing.Any=[]):
        return self.bot.database.user_channel_settings.find_all_by_setting(
            self.id, setting, default)

    def set_own_nickname(self, nickname: str):
        self.nickname = nickname
        self.nickname_lower = utils.irc.lower(self.case_mapping, nickname)
    def is_own_nickname(self, nickname: str):
        return utils.irc.equals(self.case_mapping, nickname, self.nickname)

    def add_own_mode(self, mode: str, arg: str=None):
        self.own_modes[mode] = arg
    def remove_own_mode(self, mode: str):
        del self.own_modes[mode]
    def change_own_mode(self, remove: bool, mode: str, arg: str=None):
        if remove:
            self.remove_own_mode(mode)
        else:
            self.add_own_mode(mode, arg)

    def has_user(self, nickname: str):
        return utils.irc.lower(self.case_mapping, nickname) in self.users
    def get_user(self, nickname: str, create: bool=True):
        if not self.has_user(nickname) and create:
            user_id = self.get_user_id(nickname)
            new_user = IRCUser.User(nickname, user_id, self, self.bot)
            self.events.on("new.user").call(user=new_user, server=self)
            self.users[new_user.nickname_lower] = new_user
            self.new_users.add(new_user)
        return self.users.get(utils.irc.lower(self.case_mapping, nickname),
            None)
    def get_user_id(self, nickname: str):
        self.bot.database.users.add(self.id, nickname)
        return self.bot.database.users.get_id(self.id, nickname)
    def remove_user(self, user: IRCUser.User):
        del self.users[user.nickname_lower]
        for channel in user.channels:
            channel.remove_user(user)

    def change_user_nickname(self, old_nickname: str, new_nickname: str):
        user = self.users.pop(utils.irc.lower(self.case_mapping, old_nickname))
        user._id = self.get_user_id(new_nickname)
        self.users[utils.irc.lower(self.case_mapping, new_nickname)] = user

    def parse_data(self, line: str):
        if not line:
            return
        self.events.on("raw").call_unsafe(server=self, line=line)
        self.check_users()
    def check_users(self):
        for user in self.new_users:
            if not len(user.channels):
                self.remove_user(user)
        self.new_users.clear()
    def read(self):
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
                line = line.decode(encoding)
            except:
                self.bot.log.trace("can't decode line with '%s', falling back",
                    [encoding])
                try:
                    line = line.decode(self.get_setting(
                        "fallback-encoding", "latin-1"))
                except:
                    continue
            decoded_lines.append(line)

        self.last_read = time.monotonic()
        self.ping_sent = False
        return decoded_lines

    def until_next_ping(self):
        if self.ping_sent:
            return None
        return max(0, (self.last_read+PING_INTERVAL_SECONDS
            )-time.monotonic())
    def ping_due(self):
        return self.until_next_ping() == 0

    def until_read_timeout(self):
        return max(0, (self.last_read+READ_TIMEOUT_SECONDS
            )-time.monotonic())
    def read_timed_out(self):
        return self.until_read_timeout == 0

    def send(self, data: str):
        returned = self.events.on("preprocess.send").call_unsafe_for_result(
            server=self, line=data)
        line = returned or data

        encoded = line.split("\n")[0].strip("\r").encode("utf8")
        if len(encoded) > 450:
            encoded = encoded[:450]
        self.buffered_lines.append(encoded + b"\r\n")
        self.bot.log.debug(">%s | %s", [str(self), encoded.decode("utf8")])

    def _send(self):
        if not len(self.write_buffer):
            self.write_buffer = self.buffered_lines.pop(0)

        bytes_written = self.socket.send(self.write_buffer)
        self.bytes_written += bytes_written
        self.write_buffer = self.write_buffer[bytes_written:]

        now = time.monotonic()
        self.recent_sends.append(now)
        self.last_send = now
    def waiting_send(self):
        return bool(len(self.write_buffer)) or bool(len(self.buffered_lines))
    def throttle_done(self):
        return self.send_throttle_timeout() == 0
    def send_throttle_timeout(self):
        if len(self.write_buffer):
            return 0

        now = time.monotonic()
        popped = 0
        for i, recent_send in enumerate(self.recent_sends[:]):
            time_since = now-recent_send
            if time_since >= THROTTLE_SECONDS:
                self.recent_sends.pop(i-popped)
                popped += 1

        if len(self.recent_sends) < THROTTLE_LINES:
            return 0

        time_left = self.recent_sends[0]+THROTTLE_SECONDS
        time_left = time_left-now
        return time_left

    def send_user(self, username: str, realname: str):
        self.send("USER %s 0 * :%s" % (username, realname))
    def send_nick(self, nickname: str):
        self.send("NICK %s" % nickname)

    def send_capibility_ls(self):
        self.send("CAP LS 302")
    def queue_capability(self, capability: str):
        self._capability_queue.add(capability)
    def queue_capabilities(self, capabilities: typing.List[str]):
        self._capability_queue.update(capabilities)
    def send_capability_queue(self):
        if self.has_capability_queue():
            capabilities = " ".join(self._capability_queue)
            self._capability_queue.clear()
            self.send_capability_request(capabilities)
    def has_capability_queue(self):
        return bool(len(self._capability_queue))
    def send_capability_request(self, capability: str):
        self.send("CAP REQ :%s" % capability)
    def send_capability_end(self):
        self.send("CAP END")
    def send_authenticate(self, text: str):
        self.send("AUTHENTICATE %s" % text)
    def send_starttls(self):
        self.send("STARTTLS")

    def waiting_for_capabilities(self):
        return bool(len(self._capabilities_waiting))
    def wait_for_capability(self, capability: str):
        self._capabilities_waiting.add(capability)
    def capability_done(self, capability: str):
        self._capabilities_waiting.remove(capability)
        if self.cap_started and not self._capabilities_waiting:
            self.send_capability_end()

    def send_pass(self, password: str):
        self.send("PASS %s" % password)

    def send_ping(self, nonce: str="hello"):
        self.send("PING :%s" % nonce)
    def send_pong(self, nonce: str="hello"):
        self.send("PONG :%s" % nonce)

    def try_rejoin(self, event: EventManager.Event):
        if event["server_id"] == self.id and event["channel_name"
                ] in self.attempted_join:
            self.send_join(event["channel_name"], event["key"])
    def send_join(self, channel_name: str, key: str=None):
        self.send("JOIN %s%s" % (channel_name,
            "" if key == None else " %s" % key))
    def send_part(self, channel_name: str, reason: str=None):
        self.send("PART %s%s" % (channel_name,
            "" if reason == None else " %s" % reason))
    def send_quit(self, reason: str="Leaving"):
        self.send("QUIT :%s" % reason)

    def _tag_str(self, tags: dict):
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
            tags: dict={}):
        full_message = message if not prefix else prefix+message
        self.send("%sPRIVMSG %s :%s" % (self._tag_str(tags), target,
            full_message))

        action = full_message.startswith("\01ACTION "
            ) and full_message.endswith("\01")

        if action:
            message = full_message.split("\01ACTION ", 1)[1][:-1]

        full_message_split = full_message.split()
        if target in self.channels:
            channel = self.channels.get(target)
            channel.buffer.add_message(None, message, action, tags, True)
            self.events.on("self.message.channel").call(
                message=full_message, message_split=full_message_split,
                channel=channel, action=action, server=self)
        else:
            user = self.get_user(target)
            user.buffer.add_message(None, message, action, tags, True)
            self.events.on("self.message.private").call(
                message=full_message, message_split=full_message_split,
                    user=user, action=action, server=self)

    def send_notice(self, target: str, message: str, prefix: str=None,
            tags: dict={}):
        full_message = message if not prefix else prefix+message
        self.send("%sNOTICE %s :%s" % (self._tag_str(tags), target,
            full_message))
        if target in self.channels:
            self.channels.get(target).buffer.add_notice(None, message, tags,
                True)
        else:
            self.get_user(target).buffer.add_notice(None, message, tags,
                True)

    def send_mode(self, target: str, mode: str=None, args: str=None):
        self.send("MODE %s%s%s" % (target, "" if mode == None else " %s" % mode,
            "" if args == None else " %s" % args))

    def send_topic(self, channel_name: str, topic: str):
        self.send("TOPIC %s :%s" % (channel_name, topic))
    def send_kick(self, channel_name: str, target: str, reason: str=None):
        self.send("KICK %s %s%s" % (channel_name, target,
            "" if reason == None else " :%s" % reason))
    def send_names(self, channel_name: str):
        self.send("NAMES %s" % channel_name)
    def send_list(self, search_for: str=None):
        self.send(
            "LIST%s" % "" if search_for == None else " %s" % search_for)
    def send_invite(self, target: str, channel_name: str):
        self.send("INVITE %s %s" % (target, channel_name))

    def send_whois(self, target: str):
        self.send("WHOIS %s" % target)
    def send_whowas(self, target: str, amount: int=None, server: str=None):
        self.send("WHOWAS %s%s%s" % (target,
            "" if amount == None else " %s" % amount,
            "" if server == None else " :%s" % server))
    def send_who(self, filter: str=None):
        self.send("WHO%s" % ("" if filter == None else " %s" % filter))
    def send_whox(self, mask: str, filter: str, fields: str, label: str=None):
        self.send("WHO %s %s%%%s%s" % (mask, filter, fields,
            ","+label if label else ""))
