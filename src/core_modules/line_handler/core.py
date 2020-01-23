import codecs, re

RE_ISUPPORT_ESCAPE = re.compile(r"\\x(\d\d)", re.I)
RE_MODES = re.compile(r"[-+]\w+")

def ping(event):
    event["server"].send_pong(event["line"].args[0])

def handle_001(event):
    event["server"].socket.enable_write_throttle()
    event["server"].name = event["line"].source.hostmask
    event["server"].set_own_nickname(event["line"].args[0])
    event["server"].send_whois(event["server"].nickname)
    event["server"].send_mode(event["server"].nickname)
    event["server"].connected = True

def handle_005(events, event):
    isupport_list = event["line"].args[1:-1]
    isupport = {}

    for i, item in enumerate(isupport_list):
        key, sep, value = item.partition("=")
        if value:
            for match in RE_ISUPPORT_ESCAPE.finditer(value):
                char = codecs.decode(match.group(1), "hex").decode("ascii")
                value.replace(match.group(0), char)

        if sep:
            isupport[key] = value
        else:
            isupport[key] = None
    event["server"].isupport.update(isupport)

    if "NAMESX" in isupport and not event["server"].has_capability_str(
            "multi-prefix"):
        event["server"].send_raw("PROTOCTL NAMESX")

    if "PREFIX" in isupport:
        modes, symbols = isupport["PREFIX"][1:].split(")", 1)
        event["server"].prefix_symbols.clear()
        event["server"].prefix_modes.clear()
        for symbol, mode in zip(symbols, modes):
            event["server"].prefix_symbols[symbol] = mode
            event["server"].prefix_modes[mode] = symbol

    if "CHANMODES" in isupport:
        modes = isupport["CHANMODES"].split(",", 3)
        event["server"].channel_list_modes = list(modes[0])
        event["server"].channel_parametered_modes = list(modes[1])
        event["server"].channel_setting_modes = list(modes[2])
        event["server"].channel_modes = list(modes[3])
    if "CHANTYPES" in isupport:
        event["server"].channel_types = list(isupport["CHANTYPES"])
    if "CASEMAPPING" in isupport and isupport["CASEMAPPING"]:
        event["server"].case_mapping = isupport["CASEMAPPING"]
    if "STATUSMSG" in isupport:
        event["server"].statusmsg = list(isupport["STATUSMSG"])
    if "QUIET" in isupport:
        quiet = dict(enumerate(isupport["QUIET"].split(",")))
        prefix = quiet.get(1, "")
        list_numeric = qiuet.get(2, "367") # RPL_BANLIST
        end_numeric = quiet.get(3, "368")  # RPL_ENDOFBANLIST
        event["server"].quiet = [quiet[0], prefix, list_numeric, end_numeric]

    events.on("received.005").call(isupport=isupport,
        server=event["server"])

def handle_004(event):
    event["server"].version = event["line"].args[2]

def motd_start(event):
    event["server"].motd_lines.clear()
def motd_line(event):
    event["server"].motd_lines.append(event["line"].args[1])

def _own_modes(server, modes):
    mode_chunks = RE_MODES.findall(modes)
    for chunk in mode_chunks:
        remove = chunk[0] == "-"
        for mode in chunk[1:]:
            server.change_own_mode(remove, mode)

def mode(events, event):
    user = event["server"].get_user(event["line"].source.nickname)
    target = event["line"].args[0]
    is_channel = event["server"].is_channel(target)
    if is_channel:
        channel = event["server"].channels.get(target)
        modes = event["line"].args[1]
        args  = event["line"].args[2:]

        new_modes = channel.parse_modes(modes, args[:])

        events.on("received.mode.channel").call(modes=new_modes,
            channel=channel, server=event["server"], user=user, modes_str=modes,
            args_str=args)
    elif event["server"].is_own_nickname(target):
        modes = event["line"].args[1]
        _own_modes(event["server"], modes)

        events.on("self.mode").call(modes=modes, server=event["server"])
        event["server"].send_who(event["server"].nickname)

def handle_221(event):
    _own_modes(event["server"], event["line"].args[1])

def invite(events, event):
    target_channel = event["line"].args[1]
    user = event["server"].get_user(event["line"].source.nickname)
    target_user = event["server"].get_user(event["line"].args[0])
    events.on("received.invite").call(user=user, target_channel=target_channel,
        server=event["server"], target_user=target_user)

def handle_352(events, event):
    nickname = event["line"].args[5]
    username = event["line"].args[2]
    hostname = event["line"].args[3]

    if event["server"].is_own_nickname(nickname):
        event["server"].username = username
        event["server"].hostname = hostname

    target = event["server"].get_user(nickname)
    target.username = username
    target.hostname = hostname
    events.on("received.who").call(server=event["server"],
        user=target)

def handle_354(events, event):
    if event["line"].args[1] == "111":
        nickname = event["line"].args[4]
        username = event["line"].args[2]
        hostname = event["line"].args[3]
        realname = event["line"].args[6]
        account = event["line"].args[5]

        if event["server"].is_own_nickname(nickname):
            event["server"].username = username
            event["server"].hostname = hostname
            event["server"].realname = realname

        target = event["server"].get_user(nickname)
        target.username = username
        target.hostname = hostname
        target.realname = realname
        if not account == "0":
            target.account = account
        else:
            target.account = None
        events.on("received.whox").call(server=event["server"],
            user=target)

def handle_315(events, event):
    target = event["line"].args[1]
    if target in event["server"].channels:
        channel = event["server"].channels.get(target)
        events.on("received.endofwho").call(server=event["server"],
            channel=channel)
        channel.seen_who = True

def _nick_in_use(server):
    new_nick = "%s|" % server.connection_params.nickname
    server.send_nick(new_nick)

def handle_433(event):
    _nick_in_use(event["server"])
def handle_437(event):
    _nick_in_use(event["server"])
