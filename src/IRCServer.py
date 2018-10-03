import collections, socket, ssl, sys, time
from src import IRCChannel, IRCObject, IRCUser, utils

THROTTLE_LINES = 4
THROTTLE_SECONDS = 1
READ_TIMEOUT_SECONDS = 120
PING_INTERVAL_SECONDS = 30

class Server(IRCObject.Object):
    def __init__(self, bot, events, id, alias, hostname, port, password,
            ipv4, tls, bindhost, nickname, username, realname):
        self.connected = False
        self.bot = bot
        self.events = events
        self.id = id
        self.alias = alias
        self.target_hostname = hostname
        self.port = port
        self.tls = tls
        self.password = password
        self.ipv4 = ipv4
        self.original_nickname = nickname
        self.original_username = username or nickname
        self.original_realname = realname or nickname
        self.name = None

        self._capability_queue = set([])
        self._capabilities_waiting = set([])
        self.capabilities = set([])
        self.server_capabilities = {}
        self.batches = {}

        self.write_buffer = b""
        self.buffered_lines = []
        self.read_buffer = b""
        self.recent_sends = []

        self.users = {}
        self.new_users = set([])
        self.channels = {}

        self.own_modes = {}
        self.mode_prefixes = collections.OrderedDict(
            {"@": "o", "+": "v"})
        self.channel_modes = []
        self.channel_types = ["#"]
        self.case_mapping = "rfc1459"

        self.last_read = time.monotonic()
        self.last_send = None

        self.attempted_join = {}
        self.ping_sent = False

        if ipv4:
            self.socket = socket.socket(socket.AF_INET,
                socket.SOCK_STREAM)
        else:
            self.socket = socket.socket(socket.AF_INET6,
                socket.SOCK_STREAM)

        if bindhost:
            self.socket.bind((bindhost, 0))
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.socket.settimeout(5.0)

        if self.tls:
            self.tls_wrap()
        self.cached_fileno = self.socket.fileno()
        self.events.on("timer.rejoin").hook(self.try_rejoin)

    def __repr__(self):
        return "IRCServer.Server(%s)" % self.__str__()
    def __str__(self):
        if self.alias:
            return self.alias
        return "%s:%s%s" % (self.target_hostname, "+" if self.tls else "",
            self.port)
    def fileno(self):
        fileno = self.socket.fileno()
        return self.cached_fileno if fileno == -1 else fileno

    def tls_wrap(self):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1

        context.load_default_certs()
        if self.get_setting("ssl-verify", True):
            context.verify_mode = ssl.CERT_REQUIRED

        client_certificate = self.bot.config.get("ssl-certificate", None)
        client_key = self.bot.config.get("ssl-key", None)
        if client_certificate and client_key:
            context.load_cert_chain(client_certificate, keyfile=client_key)

        self.socket = context.wrap_socket(self.socket)

    def connect(self):
        self.socket.connect((self.target_hostname, self.port))
        self.send_capibility_ls()

        if self.password:
            self.send_pass(self.password)

        self.send_user(self.original_username, self.original_realname)
        self.send_nick(self.original_nickname)
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

    def set_setting(self, setting, value):
        self.bot.database.server_settings.set(self.id, setting,
            value)
    def get_setting(self, setting, default=None):
        return self.bot.database.server_settings.get(self.id,
            setting, default)
    def find_settings(self, pattern, default=[]):
        return self.bot.database.server_settings.find(self.id,
            pattern, default)
    def find_settings_prefix(self, prefix, default=[]):
        return self.bot.database.server_settings.find_prefix(
            self.id, prefix, default)
    def del_setting(self, setting):
        self.bot.database.server_settings.delete(self.id, setting)
    def get_all_user_settings(self, setting, default=[]):
        return self.bot.database.user_settings.find_all_by_setting(
            self.id, setting, default)
    def find_all_user_channel_settings(self, setting, default=[]):
        return self.bot.database.user_channel_settings.find_all_by_setting(
            self.id, setting, default)

    def set_own_nickname(self, nickname):
        self.nickname = nickname
        self.nickname_lower = utils.irc.lower(self, nickname)
    def is_own_nickname(self, nickname):
        return utils.irc.equals(self, nickname, self.nickname)

    def add_own_mode(self, mode, arg=None):
        self.own_modes[mode] = arg
    def remove_own_mode(self, mode):
        del self.own_modes[mode]
    def change_own_mode(self, remove, mode, arg=None):
        if remove:
            self.remove_own_mode(mode)
        else:
            self.add_own_mode(mode, arg)

    def has_user(self, nickname):
        return utils.irc.lower(self, nickname) in self.users
    def get_user(self, nickname, create=True):
        if not self.has_user(nickname) and create:
            user_id = self.get_user_id(nickname)
            new_user = IRCUser.User(nickname, user_id, self, self.bot)
            self.events.on("new.user").call(user=new_user, server=self)
            self.users[new_user.nickname_lower] = new_user
            self.new_users.add(new_user)
        return self.users.get(utils.irc.lower(self, nickname), None)
    def get_user_id(self, nickname):
        self.bot.database.users.add(self.id, nickname)
        return self.bot.database.users.get_id(self.id, nickname)
    def remove_user(self, user):
        del self.users[user.nickname_lower]
        for channel in user.channels:
            channel.remove_user(user)

    def change_user_nickname(self, old_nickname, new_nickname):
        user = self.users.pop(utils.irc.lower(self, old_nickname))
        user._id = self.get_user_id(new_nickname)
        self.users[utils.irc.lower(self, new_nickname)] = user
    def has_channel(self, channel_name):
        return channel_name[0] in self.channel_types and utils.irc.lower(
            self, channel_name) in self.channels
    def get_channel(self, channel_name):
        if not self.has_channel(channel_name):
            channel_id = self.get_channel_id(channel_name)
            new_channel = IRCChannel.Channel(channel_name, channel_id,
                self, self.bot)
            self.events.on("new.channel").call(channel=new_channel,
                server=self)
            self.channels[new_channel.name] = new_channel
        return self.channels[utils.irc.lower(self, channel_name)]
    def get_channel_id(self, channel_name):
        self.bot.database.channels.add(self.id, channel_name)
        return self.bot.database.channels.get_id(self.id, channel_name)
    def remove_channel(self, channel):
        for user in channel.users:
            user.part_channel(channel)
        del self.channels[channel.name]
    def parse_line(self, line):
        if not line:
            return
        self.events.on("raw").call(server=self, line=line)
        self.check_users()
    def check_users(self):
        for user in self.new_users:
            if not len(user.channels):
                self.remove_user(user)
        self.new_users.clear()
    def read(self):
        data = b""
        try:
            data = self.read_buffer + self.socket.recv(4096)
        except (ConnectionResetError, socket.timeout):
            self.disconnect()
            return []
        self.read_buffer = b""
        data_lines = [line.strip(b"\r") for line in data.split(b"\n")]
        if data_lines[-1]:
            self.read_buffer = data_lines[-1]
        data_lines.pop(-1)
        decoded_lines = []
        for line in data_lines:
            try:
                line = line.decode(self.get_setting(
                    "encoding", "utf8"))
            except:
                try:
                    line = line.decode(self.get_setting(
                        "fallback-encoding", "latin-1"))
                except:
                    continue
            decoded_lines.append(line)
        if not decoded_lines:
            self.disconnect()
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

    def send(self, data):
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
        self.write_buffer = self.write_buffer[self.socket.send(
            self.write_buffer):]

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

    def send_user(self, username, realname):
        self.send("USER %s 0 * :%s" % (username, realname))
    def send_nick(self, nickname):
        self.send("NICK %s" % nickname)

    def send_capibility_ls(self):
        self.send("CAP LS 302")
    def queue_capability(self, capability):
        self._capability_queue.add(capability)
    def queue_capabilities(self, capabilities):
        self._capability_queue.update(capabilities)
    def send_capability_queue(self):
        if self.has_capability_queue():
            capabilities = " ".join(self._capability_queue)
            self._capability_queue.clear()
            self.send_capability_request(capabilities)
    def has_capability_queue(self):
        return bool(len(self._capability_queue))
    def send_capability_request(self, capability):
        self.send("CAP REQ :%s" % capability)
    def send_capability_end(self):
        self.send("CAP END")
    def send_authenticate(self, text):
        self.send("AUTHENTICATE %s" % text)
    def send_starttls(self):
        self.send("STARTTLS")

    def waiting_for_capabilities(self):
        return bool(len(self._capabilities_waiting))
    def wait_for_capability(self, capability):
        self._capabilities_waiting.add(capability)
    def capability_done(self, capability):
        self._capabilities_waiting.remove(capability)
        if not self._capabilities_waiting:
            self.send_capability_end()

    def send_pass(self, password):
        self.send("PASS %s" % password)

    def send_ping(self, nonce="hello"):
        self.send("PING :%s" % nonce)
    def send_pong(self, nonce="hello"):
        self.send("PONG :%s" % nonce)

    def try_rejoin(self, event):
        if event["server_id"] == self.id and event["channel_name"
                ] in self.attempted_join:
            self.send_join(event["channel_name"], event["key"])
    def send_join(self, channel_name, key=None):
        self.send("JOIN %s%s" % (channel_name,
            "" if key == None else " %s" % key))
    def send_part(self, channel_name, reason=None):
        self.send("PART %s%s" % (channel_name,
            "" if reason == None else " %s" % reason))
    def send_quit(self, reason="Leaving"):
        self.send("QUIT :%s" % reason)

    def _tag_str(self, tags):
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

    def send_message(self, target, message, prefix=None, tags={}):
        full_message = message if not prefix else prefix+message
        self.send("%sPRIVMSG %s :%s" % (self._tag_str(tags), target,
            full_message))

        action = full_message.startswith("\01ACTION "
            ) and full_message.endswith("\01")

        if action:
            message = full_message.split("\01ACTION ", 1)[1][:-1]

        full_message_split = full_message.split()
        if self.has_channel(target):
            channel = self.get_channel(target)
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

    def send_notice(self, target, message, prefix=None, tags={}):
        full_message = message if not prefix else prefix+message
        self.send("%sNOTICE %s :%s" % (self._tag_str(tags), target,
            full_message))
        if self.has_channel(target):
            self.get_channel(target).buffer.add_notice(None, message, tags,
                True)
        else:
            self.get_user(target).buffer.add_notice(None, message, tags,
                True)

    def send_mode(self, target, mode=None, args=None):
        self.send("MODE %s%s%s" % (target, "" if mode == None else " %s" % mode,
            "" if args == None else " %s" % args))

    def send_topic(self, channel_name, topic):
        self.send("TOPIC %s :%s" % (channel_name, topic))
    def send_kick(self, channel_name, target, reason=None):
        self.send("KICK %s %s%s" % (channel_name, target,
            "" if reason == None else " :%s" % reason))
    def send_names(self, channel_name):
        self.send("NAMES %s" % channel_name)
    def send_list(self, search_for=None):
        self.send(
            "LIST%s" % "" if search_for == None else " %s" % search_for)
    def send_invite(self, target, channel_name):
        self.send("INVITE %s %s" % (target, channel_name))

    def send_whois(self, target):
        self.send("WHOIS %s" % target)
    def send_whowas(self, target, amount=None, server=None):
        self.send("WHOWAS %s%s%s" % (target,
            "" if amount == None else " %s" % amount,
            "" if server == None else " :%s" % server))
    def send_who(self, filter=None):
        self.send("WHO%s" % ("" if filter == None else " %s" % filter))
    def send_whox(self, mask, filter, fields, label=None):
        self.send("WHO %s %s%%%s%s" % (mask, filter, fields,
            ","+label if label else ""))
