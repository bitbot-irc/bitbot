import collections, socket, ssl, sys, time
import IRCChannel, IRCUser

THROTTLE_LINES = 4
THROTTLE_SECONDS = 1
READ_TIMEOUT_SECONDS = 120
PING_INTERVAL_SECONDS = 30

OUR_TLS_PROTOCOL = ssl.PROTOCOL_SSLv23
if hasattr(ssl, "PROTOCOL_TLS"):
    OUR_TLS_PROTOCOL = ssl.PROTOCOL_TLS

class Server(object):
    def __init__(self, id, hostname, port, password, ipv4, tls,
            nickname, username, realname, bot):
        self.connected = False
        self.bot = bot
        self.id = id
        self.target_hostname = hostname
        self.port = port
        self.tls = tls
        self.password = password
        self.ipv4 = ipv4
        self.original_nickname = nickname
        self.original_username = username or nickname
        self.original_realname = realname or nickname
        self.name = None

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
        self.channel_types = []

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

        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.socket.settimeout(5.0)

        if self.tls:
            context = ssl.SSLContext(OUR_TLS_PROTOCOL)
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3
            context.options |= ssl.OP_NO_TLSv1
            self.socket = context.wrap_socket(self.socket)
        self.cached_fileno = self.socket.fileno()
        self.bot.events.on("timer").on("rejoin").hook(self.try_rejoin)

    def __repr__(self):
        return "IRCServer.Server(%s)" % self.__str__()
    def __str__(self):
        return "%s:%s%s" % (self.target_hostname, "+" if self.tls else "",
            self.port)
    def fileno(self):
        fileno = self.socket.fileno()
        return self.cached_fileno if fileno == -1 else fileno

    def connect(self):
        self.socket.connect((self.target_hostname, self.port))
        self.bot.events.on("preprocess.connect").call(server=self)

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
    def get_all_user_settings(self, setting, default):
        return self.bot.database.user_settings.find_all_by_setting(
            self.id, setting, default)

    def set_own_nickname(self, nickname):
        self.nickname = nickname
        self.nickname_lower = nickname.lower()
    def is_own_nickname(self, nickname):
        return nickname.lower() == self.nickname_lower

    def add_own_mode(self, mode, arg=None):
        self.own_modes[mode] = arg
    def remove_own_mode(self, mode):
        del self.own_modes[mode]
    def change_own_mode(self, remove, mode, arg=None):
        if remove:
            self.remove_own_mode(mode, arg)
        else:
            self.add_own_mode(mode, arg)

    def has_user(self, nickname):
        return nickname.lower() in self.users
    def get_user(self, nickname):
        if not self.has_user(nickname):
            user_id = self.get_user_id(nickname)
            new_user = IRCUser.User(nickname, user_id, self, self.bot)
            self.bot.events.on("new").on("user").call(
                user=new_user, server=self)
            self.users[new_user.nickname_lower] = new_user
            self.new_users.add(new_user)
        return self.users[nickname.lower()]
    def get_user_id(self, nickname):
        self.bot.database.users.add(self.id, nickname)
        return self.bot.database.users.get_id(self.id, nickname)
    def remove_user(self, user):
        del self.users[user.nickname_lower]
        for channel in user.channels:
            channel.remove_user(user)

    def change_user_nickname(self, old_nickname, new_nickname):
        user = self.users.pop(old_nickname.lower())
        user.id = self.get_user_id(new_nickname)
        self.users[new_nickname.lower()] = user
    def has_channel(self, channel_name):
        return channel_name[0] in self.channel_types and channel_name.lower(
            ) in self.channels
    def get_channel(self, channel_name):
        if not self.has_channel(channel_name):
            channel_id = self.get_channel_id(channel_name)
            new_channel = IRCChannel.Channel(channel_name, channel_id,
                self, self.bot)
            self.bot.events.on("new").on("channel").call(
                channel=new_channel, server=self)
            self.channels[new_channel.name] = new_channel
        return self.channels[channel_name.lower()]
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
        self.bot.line_handler.handle(self, line)
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
        except ConnectionResetError:
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
        encoded = data.split("\n")[0].strip("\r").encode("utf8")
        if len(encoded) > 450:
            encoded = encoded[:450]
        self.buffered_lines.append(encoded + b"\r\n")
        if self.bot.args.verbose:
            self.bot.log.info(">%s | %s", [str(self), encoded.decode("utf8")])
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
        self.send("USER %s - - :%s" % (username, realname))
    def send_nick(self, nickname):
        self.send("NICK %s" % nickname)

    def send_capability_request(self, capname):
        self.send("CAP REQ :%s" % capname)
    def send_capability_end(self):
        self.send("CAP END")
    def send_authenticate(self, text):
        self.send("AUTHENTICATE %s" % text)

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

    def send_message(self, target, message, prefix=None):
        full_message = message if not prefix else prefix+message

        self.send("PRIVMSG %s :%s" % (target, full_message))
        action = full_message.startswith("\01ACTION "
            ) and full_message.endswith("\01")

        if action:
            message = full_message.split("\01ACTION ", 1)[1][:-1]

        full_message_split = full_message.split()
        if self.has_channel(target):
            channel = self.get_channel(target)
            channel.buffer.add_line(None, message, action, True)
            self.bot.events.on("self").on("message").on("channel").call(
                message=full_message, message_split=full_message_split,
                channel=channel, action=action, server=self)
        else:
            user = self.get_user(target)
            user.buffer.add_line(None, message, action, True)
            self.bot.events.on("self").on("message").on("private").call(
                message=full_message, message_split=full_message_split,
                user=user, action=action, server=self)

    def send_notice(self, target, message):
        self.send("NOTICE %s :%s" % (target, message))

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
