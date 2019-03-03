import codecs, re

RE_ISUPPORT_ESCAPE = re.compile(r"\\x(\d\d)", re.I)
RE_MODES = re.compile(r"[-+]\w+")

def ping(event):
    event["server"].send_pong(event["args"][0])

def handle_001(event):
    event["server"].socket.set_write_throttling(True)
    event["server"].name = event["prefix"].hostmask
    event["server"].set_own_nickname(event["args"][0])
    event["server"].send_whois(event["server"].nickname)

def handle_005(events, event):
    isupport_list = event["args"][1:-1]
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

    if "NAMESX" in isupport and not event["server"].has_capability(
            "multi-prefix"):
        event["server"].send("PROTOCTL NAMESX")

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
        event["server"].channel_paramatered_modes = list(modes[1])
        event["server"].channel_setting_modes = list(modes[2])
        event["server"].channel_modes = list(modes[3])
    if "CHANTYPES" in isupport:
        event["server"].channel_types = list(isupport["CHANTYPES"])
    if "CASEMAPPING" in isupport:
        event["server"].case_mapping = isupport["CASEMAPPING"]

    events.on("received.005").call(isupport=isupport,
        server=event["server"])

def motd_start(event):
    event["server"].motd_lines.clear()
def motd_line(event):
    event["server"].motd_lines.append(event["args"][1])

def mode(events, event):
    user = event["server"].get_user(event["prefix"].nickname)
    target = event["args"][0]
    is_channel = target[0] in event["server"].channel_types
    if is_channel:
        channel = event["server"].channels.get(target)
        args  = event["args"][2:]
        _args = args[:]
        modes = RE_MODES.findall(event["args"][1])
        for chunk in modes:
            remove = chunk[0] == "-"
            for mode in chunk[1:]:
                if mode in event["server"].channel_modes:
                    channel.change_mode(remove, mode)
                elif mode in event["server"].prefix_modes and len(args):
                    channel.change_mode(remove, mode, args.pop(0))
                elif (mode in event["server"].channel_list_modes or
                        mode in event["server"].channel_paramatered_modes):
                    args.pop(0)
                elif not remove:
                    args.pop(0)
        events.on("received.mode.channel").call(modes=modes, mode_args=_args,
            channel=channel, server=event["server"], user=user)
    elif event["server"].is_own_nickname(target):
        modes = RE_MODES.findall(event["args"][1])
        for chunk in modes:
            remove = chunk[0] == "-"
            for mode in chunk[1:]:
                event["server"].change_own_mode(remove, mode)
        events.on("self.mode").call(modes=modes, server=event["server"])
        event["server"].send_who(event["server"].nickname)

def invite(events, event):
    target_channel = event["args"][1]
    user = event["server"].get_user(event["prefix"].nickname)
    target_user = event["server"].get_user(event["args"][0])
    events.on("received.invite").call(user=user, target_channel=target_channel,
        server=event["server"], target_user=target_user)

def handle_352(event):
    nickname = event["args"][5]
    if not event["server"].is_own_nickname(nickname):
        target = event["server"].get_user(nickname)
    else:
        target = event["server"]
    target.username = event["args"][2]
    target.hostname = event["args"][3]

def handle_354(event):
    if event["args"][1] == "111":
        nickname = event["args"][4]

        if not event["server"].is_own_nickname(nickname):
            target = event["server"].get_user(nickname)

            account = event["args"][5]
            if not account == "0":
                target.identified_account = account
            else:
                target.identified_account = None
        else:
            target = event["server"]

        target.username = event["args"][2]
        target.hostname = event["args"][3]
        target.realname = event["args"][6]

def handle_433(event):
    new_nick = "%s|" % event["server"].connection_params.nickname
    event["server"].send_nick(new_nick)
