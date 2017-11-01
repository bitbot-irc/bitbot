import re, threading

import Utils

RE_PREFIXES = re.compile(r"\bPREFIX=\((\w+)\)(\W+)(?:\b|$)")
RE_CHANMODES = re.compile(
    r"\bCHANMODES=(\w*),(\w*),(\w*),(\w*)(?:\b|$)")
RE_CHANTYPES = re.compile(r"\bCHANTYPES=(\W+)(?:\b|$)")

handlers = {}
descriptions = {}
default_events = {}
current_description = None
current_default_event = False
handle_lock = threading.Lock()
bot = None

class LineData:
    def __init__(self, line, line_split, prefix, command, args, is_final, server):
        self.line, self.prefix = line, prefix
        self.command, self.args = command, args
        self.is_final = is_final,
        self.server, self.line_split = server, line_split

    def map(self):
        return {
            "line": self.line, "line_split": self.line_split,
            "prefix": self.prefix, "command": self.command,
            "args":  self.args, "is_final": self.is_final,
            "server": self.server,
            }

def handler(f=None, description=None, default_event=False):
    global current_description, current_default_event
    if not f:
        current_description = description
        current_default_event = default_event
        return handler
    name = f.__name__.split("handle_")[1].upper()
    handlers[name] = f

    descriptions[name] = current_description
    default_events[name] = current_default_event
    current_description, current_default_event = None, False

def handle(line, prefix, command, args, is_final, _bot, server):
    global bot
    line_split = line.split(" ")
    data = LineData(line, line_split, prefix, command, args, is_final, server)
    handler_function = None

    if command in handlers:
        handler_function = handlers[command]
    if default_events.get(command, False) or not command in handlers:
        if command.isdigit():
            _bot.events.on("received").on("numeric").on(
                command).call(data=data, number=command)
        else:
            _bot.events.on("received").on(command).call(data=data)
    if handler_function:
        with handle_lock:
            bot = _bot
            handler_function(data)

@handler(description="reply to a ping")
def handle_PING(data):
    nonce = data.args[0]
    data.server.send_pong(nonce)
    bot.events.on("received").on("ping").call(data=data, nonce=nonce)

@handler(description="the first line sent to a registered client", default_event=True)
def handle_001(data):
    server = data.server
    server.set_own_nickname(data.args[0])
    server.send_whois(server.nickname)

@handler(description="the extra supported things line")
def handle_005(data):
    server = data.server
    isupport_line = " ".join(data.args[1:])
    if "NAMESX" in data.line:
        server.send("PROTOCTL NAMESX")
    match = re.search(RE_PREFIXES, isupport_line)
    if match:
        modes = match.group(1)
        prefixes = match.group(2)
        for i, prefix in enumerate(prefixes):
            if i < len(modes):
                server.mode_prefixes[prefix] = modes[i]
    match = re.search(RE_CHANMODES, isupport_line)
    if match:
        server.channel_modes = list(match.group(4))
    match = re.search(RE_CHANTYPES, isupport_line)
    if match:
        server.channel_types = list(match.group(1))
    bot.events.on("received").on("numeric").on("005").call(
        data=data, isupport=isupport_line, number="005")

@handler(description="whois respose (nickname, username, realname, hostname)", default_event=True)
def handle_311(data):
    server = data.server
    nickname = data.args[1]
    if server.is_own_nickname(nickname):
        target = server
    else:
        target = server.get_user(nickname)
    target.username = data.args[2]
    target.hostname = data.args[3]
    target.realname = data.args[-1]

@handler(description="on-join channel topic line", default_event=True)
def handle_332(data):
    channel = data.server.get_channel(data.args[1])
    topic = data.args[2]
    channel.set_topic(topic)

@handler(description="on-join channel topic set by/at", default_event=True)
def handle_333(data):
    channel = data.server.get_channel(data.args[1])
    topic_setter_hostmask = data.args[2]
    nickname, username, hostname = Utils.seperate_hostmask(
        topic_setter_hostmask)
    topic_time = int(data.args[3]) if data.args[3].isdigit() else None
    channel.set_topic_setter(nickname, username, hostname)
    channel.set_topic_time(topic_time)

@handler(description="on-join user list with status symbols", default_event=True)
def handle_353(data):
    server = data.server
    channel = server.get_channel(data.args[2])
    nicknames = data.args[3].split()
    for nickname in nicknames:
        if nickname.strip():
            modes = set([])
            while nickname[0] in server.mode_prefixes:
                modes.add(server.mode_prefixes[nickname[0]])
                nickname = nickname[1:]
            user = server.get_user(nickname)
            user.join_channel(channel)
            channel.add_user(user)
            for mode in modes:
                channel.add_mode(mode, nickname)

@handler(description="on user joining channel")
def handle_JOIN(data):
    server = data.server
    nickname, username, hostname = Utils.seperate_hostmask(data.prefix)
    channel = server.get_channel(Utils.remove_colon(data.args[0]))
    if not server.is_own_nickname(nickname):
        user = server.get_user(nickname)
        if not server.has_user(nickname):
            user.username = username
            user.hostname = hostname
        channel.add_user(user)
        user.join_channel(channel)
        bot.events.on("received").on("join").call(data=data, channel=channel,
            user=user)
    else:
        if channel.name in server.attempted_join:
            del server.attempted_join[channel.name]
        bot.events.on("self").on("join").call(data=data, channel=channel)
        server.send_who(channel.name)
        channel.send_mode()

@handler(description="on user parting channel")
def handle_PART(data):
    server = data.server
    nickname, username, hostname = Utils.seperate_hostmask(data.prefix)
    channel = server.get_channel(data.args[0])
    reason = data.args[1] if len(data.args)>1 else ""
    if not server.is_own_nickname(nickname):
        user = server.get_user(nickname)
        bot.events.on("received").on("part").call(data=data, channel=channel,
            reason=reason, user=user)
        channel.remove_user(user)
        user.part_channel(channel)
        if not len(user.channels):
            server.remove_user(user)
    else:
        server.remove_channel(channel)
        bot.events.on("self").on("part").call(data=data, channel=channel,
            reason=reason)

@handler(description="unknown command sent by us, oops!", default_event=True)
def handle_421(data):
    print("warning: unknown command '%s'." % data.args[1])

@handler(description="a user has disconnected!")
def handle_QUIT(data):
    server = data.server
    nickname, username, hostname = Utils.seperate_hostmask(data.prefix)
    reason = data.args[0] if len(data.args) else None
    if not server.is_own_nickname(nickname):
        user = server.get_user(nickname)
        server.remove_user(user)
        bot.events.on("received").on("quit").call(data=data, reason=reason,
            user=user)
    else:
        server.disconnect()

@handler(description="The server is telling us about its capabilities!")
def handle_CAP(data):
    capibility_list = []
    if len(data.args) > 2:
        capability_list = data.args[2].split()
    bot.events.on("received").on("cap").call(data=data,
        subcommand=data.args[1], capabilities=capability_list)

@handler(description="The server is asking for authentication")
def handle_AUTHENTICATE(data):
    bot.events.on("received").on("authenticate").call(data=data,
        message=data.args[0]
        )

@handler(description="someone has changed their nickname")
def handle_NICK(data):
    server = data.server
    nickname, username, hostname = Utils.seperate_hostmask(data.prefix)
    new_nickname = data.args[0]
    if not server.is_own_nickname(nickname):
        user = server.get_user(nickname)
        old_nickname = user.nickname
        user.set_nickname(new_nickname)
        server.change_user_nickname(old_nickname, new_nickname)
        bot.events.on("received").on("nick").call(data=data,
            new_nickname=new_nickname, old_nickname=old_nickname,
            user=user)
    else:
        old_nickname = server.nickname
        server.set_own_nickname(new_nickname)
        bot.events.on("self").on("nick").call(line=line,
            line_split=line_split, server=server,
            new_nickname=new_nickname, old_nickname=old_nickname)

@handler(description="something's mode has changed")
def handle_MODE(data):
    server = data.server
    nickname, username, hostname = Utils.seperate_hostmask(data.prefix)
    target = data.args[0]
    is_channel = target[0] in server.channel_types
    if is_channel:
        channel = server.get_channel(target)
        remove = False
        args  = data.args[2:]
        modes = data.args[1]
        for i, char in enumerate(modes):
            if char == "+":
                remove = False
            elif char == "-":
                remove = True
            else:
                if char in server.channel_modes:
                    if remove:
                        channel.remove_mode(char)
                    else:
                        channel.add_mode(char)
                elif char in server.mode_prefixes.values() and len(args):
                    nickname = args.pop(0)
                    if remove:
                        channel.remove_mode(char, nickname)
                    else:
                        channel.add_mode(char, nickname)
                elif len(args):
                    args.pop(0)
        bot.events.on("received").on("mode").call(
            data=data, modes=modes, args=args, channel=channel)
    elif server.is_own_nickname(target):
        modes = Utils.remove_colon(data.args[1])
        remove = False
        for i, char in enumerate(modes):
            if char == "+":
                remove = False
            elif char == "-":
                remove = True
            else:
                if remove:
                    server.remove_own_mode(char)
                else:
                    server.add_own_mode(char)
        bot.events.on("self").on("mode").call(data=data, modes=modes)
#:nick!user@host MODE #chan +v-v nick nick

@handler(description="I've been invited somewhere")
def handle_INVITE(data):
    nickname, username, hostname = Utils.seperate_hostmask(data.prefix)
    target_channel = Utils.remove_colon(data.args[1])
    user = data.server.get_user(nickname)
    bot.events.on("received").on("invite").call(
        data=data, user=user, target_channel=target_channel)

@handler(description="we've received a message")
def handle_PRIVMSG(data):
    server = data.server
    nickname, username, hostname = Utils.seperate_hostmask(data.prefix)
    user = server.get_user(nickname)
    message = data.args[1]
    message_split = message.split(" ")
    target = data.args[0]
    action = message.startswith("\01ACTION ") and message.endswith("\01")
    if action:
        message = message.replace("\01ACTION ", "", 1)[:-1]
    if target[0] in server.channel_types:
        channel = server.get_channel(data.args[0])
        bot.events.on("received").on("message").on("channel").call(
            data=data, user=user, message=message, message_split=message_split,
            channel=channel, action=action)
        channel.log.add_line(user.nickname, message, action)
    elif server.is_own_nickname(target):
        bot.events.on("received").on("message").on("private").call(
            data=data, user=user, message=message, message_split=message_split,
            action=action)
        user.log.add_line(user.nickname, message, action)

@handler(description="response to a WHO command for user information", default_event=True)
def handle_352(data):
    user = data.server.get_user(data.args[5])
    user.username = data.args[2]
    user.hostname = data.args[3]

@handler(description="response to an empty mode command", default_event=True)
def handle_324(data):
    channel = data.server.get_channel(data.args[1])
    modes = data.args[2]
    if modes[0] == "+" and modes[1:]:
        for mode in modes[1:]:
            if mode in data.server.channel_modes:
                channel.add_mode(mode)

@handler(description="channel creation unix timestamp", default_event=True)
def handle_329(data):
    channel = data.server.get_channel(data.args[1])
    channel.creation_timestamp = int(data.args[2])

@handler(description="nickname already in use", default_event=True)
def handle_433(data):
    pass

@handler(description="we need a registered nickname for this channel", default_event=True)
def handle_477(data):
    bot.add_timer("rejoin", 5, channel_name=data.args[1],
        key=data.server.attempted_join[data.args[1].lower()],
        server_id=data.server.id)
#:newirc.tripsit.me 477 BitBot ##nope :Cannot join channel (+r) - you need to be identified with services
