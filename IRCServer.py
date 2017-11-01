import collections, socket, ssl, sys, time
import IRCChannel, IRCLineHandler, IRCUser

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
        self.write_buffer = b""
        self.read_buffer = b""
        self.users = {}
        self.new_users = set([])
        self.nickname_ids = {}
        self.channels = {}
        self.own_modes = set([])
        self.mode_prefixes = collections.OrderedDict()
        self.channel_modes = []
        self.channel_types = []
        self.last_read = None
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
            self.socket = context.wrap_socket(self.socket)
        self.cached_fileno = self.socket.fileno()
        self.bot.events.on("timer").on("rejoin").hook(self.try_rejoin)
    def __repr__(self):
        return "%s:%s%s" % (self.target_hostname, "+" if self.tls else "",
            self.port)
    def __str__(self):
        return repr(self)
    def fileno(self):
        fileno = self.socket.fileno()
        return self.cached_fileno if fileno == -1 else fileno
    def connect(self):
        self.socket.connect((self.target_hostname, self.port))

        if self.password:
            self.send_pass(self.password)
        # In principle, this belongs in the NS module. In reality, it's more practical to put this
        # One-off case here for SASL
        if "Nickserv" in self.bot.modules.modules and self.get_setting("nickserv-password"):
            self.send_capability_request("sasl")

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
        self.bot.database.set_server_setting(self.id, setting,
            value)
    def get_setting(self, setting, default=None):
        return self.bot.database.get_server_setting(self.id,
            setting, default)
    def find_settings(self, pattern, default=[]):
        return self.bot.database.find_server_settings(self.id,
            pattern, default)
    def del_setting(self, setting):
        self.bot.database.del_server_setting(self.id, setting)
    def set_own_nickname(self, nickname):
        self.nickname = nickname
        self.nickname_lower = nickname.lower()
    def is_own_nickname(self, nickname):
        return nickname.lower() == self.nickname_lower
    def add_own_mode(self, mode):
        self.own_modes.add(mode)
    def remove_own_mode(self, mode):
        self.own_modes.remove(mode)
    def has_user(self, nickname):
        return nickname.lower() in self.nickname_ids
    def get_user(self, nickname):
        if not self.has_user(nickname):
            new_user = IRCUser.User(nickname, self, self.bot)
            self.bot.events.on("new").on("user").call(
                user=new_user, server=self)
            self.users[new_user.id] = new_user
            self.nickname_ids[nickname.lower()] = new_user.id
            self.new_users.add(new_user)
        return self.users[self.nickname_ids[nickname.lower()]]
    def remove_user(self, user):
        print("removing %s" % user.nickname)
        del self.users[user.id]
        del self.nickname_ids[user.nickname_lower]
        for channel in user.channels:
            channel.remove_user(user)
    def change_user_nickname(self, old_nickname, new_nickname):
        self.nickname_ids[new_nickname.lower()] = self.nickname_ids.pop(old_nickname.lower())
    def has_channel(self, channel_name):
        return channel_name[0] in self.channel_types and channel_name.lower(
            ) in self.channels
    def get_channel(self, channel_name):
        if not self.has_channel(channel_name):
            new_channel = IRCChannel.Channel(channel_name, self,
                self.bot)
            self.bot.events.on("new").on("channel").call(
                channel=new_channel, server=self)
            self.channels[new_channel.name] = new_channel
        return self.channels[channel_name.lower()]
    def remove_channel(self, channel):
        for users in channel.users:
            user.part_channel(channel)
        del self.channels[channel.name]
    def parse_line(self, line):
        if not line: return
        original_line = line
        prefix, final = None, None
        if line[0]==":":
            prefix, line = line[1:].split(" ", 1)
        command, line = (line.split(" ", 1) + [""])[:2]
        if line[:1]==":":
            final, line = line[1:], ""
        elif " :" in line:
            line, final = line.split(" :", 1)
        args_split = line.split(" ") if line else []
        if final: args_split.append(final)
        IRCLineHandler.handle(original_line, prefix, command, args_split, final!=None, self.bot, self)
        self.check_users()
    def check_users(self):
        for user in self.new_users:
            if not len(user.channels):
                self.remove_user(user)
        self.new_users.clear()
    def read(self):
        encoding = self.bot.database.get_server_setting(self.id,
            "encoding", "utf8")
        fallback_encoding = self.bot.database.get_server_setting(
            self.id, "fallback-encoding", "latin-1")
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
                line = line.decode(encoding)
            except:
                try:
                    line = line.decode(fallback_encoding)
                except:
                    continue
            decoded_lines.append(line)
        if not decoded_lines:
            self.disconnect()
        self.last_read = time.time()
        self.ping_sent = False
        return decoded_lines
    def send(self, data):
        encoded = data.split("\n")[0].strip("\r").encode("utf8")
        if len(encoded) > 450:
            encoded = encoded[:450]
        self.write_buffer += encoded + b"\r\n"
        if self.bot.args.verbose:
            print(encoded.decode("utf8"))
    def _send(self):
        self.write_buffer = self.write_buffer[self.socket.send(
            self.write_buffer):]
    def waiting_send(self):
        return bool(len(self.write_buffer))
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
        self.attempted_join[channel_name.lower()] = key
        self.send("JOIN %s%s" % (channel_name,
            "" if key == None else " %s" % key))
    def send_part(self, channel_name, reason=None):
        self.send("PART %s%s" % (channel_name,
            "" if reason == None else " %s" % reason))
    def send_quit(self, reason="Leaving"):
        self.send("QUIT :%s" % reason)
    def send_message(self, target, message):
        self.send("PRIVMSG %s :%s" % (target, message))
        action = message.startswith("\01ACTION ") and message.endswith(
            "\01")
        if action:
            message = message.split("\01ACTION ", 1)[1][:-1]
        if self.has_channel(target):
            self.get_channel(target).log.add_line(None, message, action, True)
        else:
            self.get_user(target).log.add_line(None, message, action, True)
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
