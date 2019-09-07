from src import utils

def handle_332(events, event):
    channel = event["server"].channels.get(event["line"].args[1])
    topic = event["line"].args.get(2)
    channel.set_topic(topic)
    events.on("received.332").call(channel=channel, server=event["server"],
        topic=topic)

def topic(events, event):
    user = event["server"].get_user(event["line"].source.nickname)
    channel = event["server"].channels.get(event["line"].args[0])
    topic = event["line"].args.get(1)
    channel.set_topic(topic)
    events.on("received.topic").call(channel=channel, server=event["server"],
        topic=topic, user=user)

def handle_333(events, event):
    channel = event["server"].channels.get(event["line"].args[1])

    topic_setter = utils.irc.seperate_hostmask(event["line"].args[2])
    topic_time = int(event["line"].args[3])

    channel.set_topic_setter(topic_setter.nickname, topic_setter.username,
        topic_setter.hostname)
    channel.set_topic_time(topic_time)
    events.on("received.333").call(channel=channel,
        setter=topic_setter.nickname, set_at=topic_time, server=event["server"])

def handle_353(event):
    channel = event["server"].channels.get(event["line"].args[2])
    nicknames = event["line"].args.get(3).split(" ")

    # there can sometimes be a dangling space at the end of a 353
    if nicknames and not nicknames[-1]:
        nicknames.pop(-1)

    for nickname in nicknames:
        modes = set([])

        while nickname[0] in event["server"].prefix_symbols:
            modes.add(event["server"].prefix_symbols[nickname[0]])
            nickname = nickname[1:]

        if event["server"].has_capability_str("userhost-in-names"):
            hostmask = utils.irc.seperate_hostmask(nickname)
            nickname = hostmask.nickname
            user = event["server"].get_user(hostmask.nickname)
            user.username = hostmask.username
            user.hostname = hostmask.hostname
        else:
            user = event["server"].get_user(nickname)
        user.join_channel(channel)
        channel.add_user(user)

        for mode in modes:
            channel.add_mode(mode, nickname)

def handle_366(event):
    event["server"].send_whox(event["line"].args[1], "n", "ahnrtu", "111")

def join(events, event):
    account = None
    realname = None
    channel_name = event["line"].args[0]

    if len(event["line"].args) == 3:
        if not event["line"].args[1] == "*":
            account = event["line"].args[1]
        realname = event["line"].args[2]

    user = event["server"].get_user(event["line"].source.nickname)

    user.username = event["line"].source.username
    user.hostname = event["line"].source.hostname
    if account:
        user.identified_account = account
        user.identified_account_id = event["server"].get_user(account).get_id()
    if realname:
        user.realname = realname

    is_self = event["server"].is_own_nickname(event["line"].source.nickname)
    if is_self:
        channel = event["server"].channels.add(channel_name)
    else:
        channel = event["server"].channels.get(channel_name)


    channel.add_user(user)
    user.join_channel(channel)

    if is_self:
        events.on("self.join").call(channel=channel, server=event["server"],
            account=account, realname=realname)
        channel.send_mode()
    else:
        events.on("received.join").call(channel=channel, user=user,
            server=event["server"], account=account, realname=realname)

def part(events, event):
    channel = event["server"].channels.get(event["line"].args[0])
    user = event["server"].get_user(event["line"].source.nickname)
    reason = event["line"].args.get(1)

    channel.remove_user(user)
    user.part_channel(channel)
    if not len(user.channels):
        event["server"].remove_user(user)

    if not event["server"].is_own_nickname(event["line"].source.nickname):
        events.on("received.part").call(channel=channel, reason=reason,
            user=user, server=event["server"])
    else:
        event["server"].channels.remove(channel)
        events.on("self.part").call(channel=channel, reason=reason,
            server=event["server"])

def handle_324(events, event):
    if event["line"].args[1] in event["server"].channels:
        channel = event["server"].channels.get(event["line"].args[1])
        modes = event["line"].args[2]
        args = event["line"].args[3:]
        new_modes = channel.parse_modes(modes, args[:])
        events.on("received.324").call(modes=new_modes,
            channel=channel, server=event["server"], mode_str=modes,
            args_str=args)

def handle_329(event):
    channel = event["server"].channels.get(event["line"].args[1])
    channel.creation_timestamp = int(event["line"].args[2])

def handle_477(timers, event):
    pass

def kick(events, event):
    user = event["server"].get_user(event["line"].source.nickname)
    target = event["line"].args[1]
    channel = event["server"].channels.get(event["line"].args[0])
    reason = event["line"].args.get(2)
    target_user = event["server"].get_user(target)

    if not event["server"].is_own_nickname(target):
        events.on("received.kick").call(channel=channel, reason=reason,
            target_user=target_user, user=user, server=event["server"])
    else:
        event["server"].channels.remove(channel)
        events.on("self.kick").call(channel=channel, reason=reason, user=user,
            server=event["server"])

    channel.remove_user(target_user)
    target_user.part_channel(channel)
    if not len(target_user.channels):
        event["server"].remove_user(target_user)

def rename(events, event):
    old_name = event["line"].args[0]
    new_name = event["line"].args[1]
    channel = event["server"].channels.get(old_name)

    event["server"].channels.rename(old_name, new_name)
    events.on("received.rename").call(channel=channel, old_name=old_name,
        new_name=new_name, reason=event["line"].args.get(2),
        server=event["server"])
