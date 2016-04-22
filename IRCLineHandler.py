import re, threading
import Utils

RE_PREFIXES = re.compile(r"\bPREFIX=\((\w+)\)(\W+)(?:\b|$)")
RE_CHANMODES = re.compile(
    r"\bCHANMODES=(\w*),(\w*),(\w*),(\w*)(?:\b|$)")
RE_CHANTYPES = re.compile(r"\bCHANTYPES=(\W+)(?:\b|$)")

handlers = {}
descriptions = {}
current_description = None
handle_lock = threading.Lock()
line, line_split, bot, server = None, None, None, None

def handler(f=None, description=None):
    global current_description
    if description:
        current_description = description
        return handler
    name = f.__name__.split("handle_")[1].upper()
    handlers[name] = f
    if current_description:
        descriptions[name] = current_description
        current_description = None
def handle(_line, _line_split, _bot, _server):
    global line, line_split, bot, server
    handler_function = None
    if len(_line_split) > 1:
        if _line_split[0][0] == ":":
            if _line_split[1] in handlers:
                    handler_function = handlers[_line_split[1]]
            elif _line_split[1].isdigit():
                _bot.events.on("received").on("numeric").on(
                    _line_split[1]).call(line=_line,
                    line_split=_line_split, server=_server,
                    number=_line_split[1])
        elif _line_split[0] in handlers:
            handler_function = handlers[_line_split[0]]
    if handler_function:
        with handle_lock:
            line, line_split, bot, server = (_line, _line_split,
                _bot, _server)
            handler_function()
            line, line_split, bot, server = None, None, None, None
@handler(description="reply to a ping")
def handle_PING():
    nonce = Utils.remove_colon(line_split[1])
    server.send_pong(Utils.remove_colon(line_split[1]))
    bot.events.on("received").on("ping").call(line=line,
        line_split=line_split, server=server, nonce=nonce)
@handler(description="the first line sent to a registered client")
def handle_001():
    server.set_own_nickname(line_split[2])
    server.send_whois(server.nickname)
    bot.events.on("received").on("numeric").on("001").call(
        line=line, line_split=line_split, server=server)
@handler(description="the extra supported things line")
def handle_005():
    isupport_line = Utils.arbitrary(line_split, 3)
    if "NAMESX" in line:
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
        line=line, line_split=line_split, server=server,
        isupport=isupport_line)
@handler(description="whois respose (nickname, username, realname, hostname)")
def handle_311():
    nickname = line_split[3]
    if server.is_own_nickname(nickname):
        target = server
    else:
        target = server.get_user(nickname)
    username = line_split[4]
    hostname = line_split[5]
    target.username = username
    target.hostname = hostname
@handler(description="on-join channel topic line")
def handle_332():
    channel = server.get_channel(line_split[3])
    topic = Utils.arbitrary(line_split, 4)
    channel.set_topic(topic)
@handler(description="on-join channel topic set by/at")
def handle_333():
    channel = server.get_channel(line_split[3])
    topic_setter_hostmask = line_split[4]
    nickname, username, hostname = Utils.seperate_hostmask(
        topic_setter_hostmask)
    topic_time = int(line_split[5]) if line_split[5].isdigit(
        ) else None
    channel.set_topic_setter(nickname, username, hostname)
    channel.set_topic_time(topic_time)
@handler(description="on-join user list with status symbols")
def handle_353():
    channel = server.get_channel(line_split[4])
    nicknames = line_split[5:]
    nicknames[0] = Utils.remove_colon(nicknames[0])
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
def handle_JOIN():
    nickname, username, hostname = Utils.seperate_hostmask(line_split[0])
    channel = server.get_channel(Utils.remove_colon(line_split[2]))
    if not server.is_own_nickname(nickname):
        user = server.get_user(nickname)
        if not server.has_user(nickname):
            user.username = username
            user.hostname = hostname
        channel.add_user(user)
        user.join_channel(channel)
        bot.events.on("received").on("join").call(line=line,
            line_split=line_split, server=server, channel=channel,
            user=user)
    else:
        if channel.name in server.attempted_join:
            del server.attempted_join[channel.name]
        bot.events.on("self").on("join").call(line=line,
            line_split=line_split, server=server, channel=channel)
        server.send_who(channel.name)
        channel.send_mode()
@handler(description="on user parting channel")
def handle_PART():
    nickname, username, hostname = Utils.seperate_hostmask(line_split[0])
    channel = server.get_channel(line_split[2])
    reason = Utils.arbitrary(line_split, 3)
    if not server.is_own_nickname(nickname):
        user = server.get_user(nickname)
        bot.events.on("received").on("part").call(line=line,
            line_split=line_split, server=server, channel=channel,
            reason=reason, user=user)
        channel.remove_user(user)
        user.part_channel(channel)
        if not len(user.channels):
            server.remove_user(user)
    else:
        server.remove_channel(channel)
        bot.events.on("self").on("part").call(line=line,
            line_split=line_split, server=server, channel=channel,
            reason=reason)
@handler(description="unknown command sent by us, oops!")
def handle_421():
    print("warning: unknown command '%s'." % line_split[3])
@handler(description="a user has disconnected!")
def handle_QUIT():
    nickname, username, hostname = Utils.seperate_hostmask(line_split[0])
    reason = Utils.arbitrary(line_split, 2)
    if not server.is_own_nickname(nickname):
        user = server.get_user(nickname)
        server.remove_user(user)
        bot.events.on("received").on("quit").call(line=line,
            line_split=line_split, server=server, reason=reason,
            user=user)
    else:
        server.disconnect()
@handler(description="someone has changed their nickname")
def handle_NICK():
    nickname, username, hostname = Utils.seperate_hostmask(line_split[0])
    new_nickname = Utils.remove_colon(line_split[2])
    if not server.is_own_nickname(nickname):
        user = server.get_user(nickname)
        old_nickname = user.nickname
        user.set_nickname(new_nickname)
        server.change_user_nickname(old_nickname, new_nickname)
        bot.events.on("received").on("nick").call(line=line,
            line_split=line_split, server=server,
            new_nickname=new_nickname, old_nickname=old_nickname,
            user=user)
    else:
        old_nickname = server.nickname
        server.set_own_nickname(new_nickname)
        bot.events.on("self").on("nick").call(line=line,
            line_split=line_split, server=server,
            new_nickname=new_nickname, old_nickname=old_nickname)
@handler(description="something's mode has changed")
def handle_MODE():
    nickname, username, hostname = Utils.seperate_hostmask(line_split[0])
    target = line_split[2]
    is_channel = target[0] in server.channel_types
    if is_channel:
        channel = server.get_channel(target)
        remove = False
        args = line_split[4:]
        modes = line_split[3]
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
                elif char in server.mode_prefixes.values():
                    nickname = args.pop(0)
                    if remove:
                        channel.remove_mode(char, nickname)
                    else:
                        channel.add_mode(char, nickname)
                else:
                    args.pop(0)
        bot.events.on("received").on("mode").call(
            line=line, line_split=line_split, server=server, modes=modes,
            args=args, channel=channel)
    elif server.is_own_nickname(target):
        modes = Utils.remove_colon(line_split[3])
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
        bot.events.on("self").on("mode").call(
            line=line, line_split=line_split, server=server, modes=modes)
@handler(description="I've been invited somewhere")
def handle_INVITE():
    nickname, username, hostname = Utils.seperate_hostmask(line_split[0])
    target_channel = Utils.remove_colon(line_split[3])
    user = server.get_user(nickname)
    bot.events.on("received").on("invite").call(
        line=line, line_split=line_split, server=server,
        user=user, target_channel=target_channel)
@handler(description="we've received a message")
def handle_PRIVMSG():
    nickname, username, hostname = Utils.seperate_hostmask(line_split[0])
    user = server.get_user(nickname)
    message = Utils.arbitrary(line_split, 3)
    message_split = message.split(" ")
    target = line_split[2]
    action = message.startswith("\01ACTION ") and message.endswith("\01")
    if action:
        message = message.replace("\01ACTION ", "", 1)[:-1]
    if target[0] in server.channel_types:
        channel = server.get_channel(line_split[2])
        bot.events.on("received").on("message").on("channel").call(
            line=line, line_split=line_split, server=server,
            user=user, message=message, message_split=message_split,
            channel=channel, action=action)
        channel.log.add_line(user.nickname, message, action)
    elif server.is_own_nickname(target):
        bot.events.on("received").on("message").on("private").call(
            line=line, line_split=line_split, server=server,
            user=user, message=message, message_split=message_split,
            action=action)
        user.log.add_line(user.nickname, message, action)
@handler(description="response to a WHO command for user information")
def handle_352():
    user = server.get_user(line_split[7])
    user.username = line_split[4]
    user.hostname = line_split[5]
@handler(description="response to an empty mode command")
def handle_324():
    channel = server.get_channel(line_split[3])
    modes = line_split[4]
    if modes[0] == "+" and modes[1:]:
        for mode in modes[1:]:
            if mode in server.channel_modes:
                channel.add_mode(mode)
@handler(description="channel creation unix timestamp")
def handle_329():
    channel = server.get_channel(line_split[3])
    channel.creation_timestamp = int(line_split[4])
@handler(description="nickname already in use")
def handle_433():
    pass
@handler(description="we need a registered nickname for this channel")
def handle_477():
    bot.add_timer("rejoin", 5, channel_name=line_split[3],
        key=server.attempted_join[line_split[3].lower()],
        server_id=server.id)
#:newirc.tripsit.me 477 BitBot ##nope :Cannot join channel (+r) - you need to be identified with services
