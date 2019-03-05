from src import utils

def handle_332(events, event):
    channel = event["server"].channels.get(event["args"][1])
    topic = event["args"].get(2)
    channel.set_topic(topic)
    events.on("received.332").call(channel=channel, server=event["server"],
        topic=topic)

def topic(events, event):
    user = event["server"].get_user(event["prefix"].nickname)
    channel = event["server"].channels.get(event["args"][0])
    topic = event["args"].get(1)
    channel.set_topic(topic)
    events.on("received.topic").call(channel=channel, server=event["server"],
        topic=topic, user=user)

def handle_333(events, event):
    channel = event["server"].channels.get(event["args"][1])

    topic_setter = utils.irc.seperate_hostmask(event["args"][2])
    topic_time = int(event["args"][3]) if event["args"][3].isdigit() else None

    channel.set_topic_setter(topic_setter.nickname, topic_setter.username,
        topic_setter.hostname)
    channel.set_topic_time(topic_time)
    events.on("received.333").call(channel=channel,
        setter=topic_setter.nickname, set_at=topic_time, server=event["server"])

def handle_353(event):
    channel = event["server"].channels.get(event["args"][2])
    nicknames = event["args"].get(3).split()
    for nickname in nicknames:
        modes = set([])

        while nickname[0] in event["server"].prefix_symbols:
            modes.add(event["server"].prefix_symbols[nickname[0]])
            nickname = nickname[1:]

        if event["server"].has_capability("userhost-in-names"):
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
    event["server"].send_whox(event["args"][1], "n", "ahnrtu", "111")

def join(events, event):
    account = None
    realname = None
    channel_name = event["args"][0]

    if len(event["args"]) == 3:
        if not event["args"][1] == "*":
            account = event["args"][1]
        realname = event["args"][2]

    user = event["server"].get_user(event["prefix"].nickname)

    if event["server"].is_own_nickname(event["prefix"].nickname):
        channel = event["server"].channels.add(channel_name)
        if channel.name in event["server"].attempted_join:
            del event["server"].attempted_join[channel.name]
        events.on("self.join").call(channel=channel, server=event["server"],
            account=account, realname=realname)
        channel.send_mode()
    else:
        channel = event["server"].channels.get(channel_name)
        events.on("received.join").call(channel=channel, user=user,
            server=event["server"], account=account, realname=realname)

    if not user.username and not user.hostname:
        user.username = event["prefix"].username
        user.hostname = event["prefix"].hostname

    if account:
        user.identified_account = account
        user.identified_account_id = event["server"].get_user(account).get_id()
    if realname:
        user.realname = realname

    channel.add_user(user)
    user.join_channel(channel)

def part(events, event):
    channel = event["server"].channels.get(event["args"][0])
    user = event["server"].get_user(event["prefix"].nickname)
    reason = event["args"].get(1)

    if not event["server"].is_own_nickname(event["prefix"].nickname):
        events.on("received.part").call(channel=channel, reason=reason,
            user=user, server=event["server"])
    else:
        events.on("self.part").call(channel=channel, reason=reason,
            server=event["server"])
        event["server"].channels.remove(channel)

    channel.remove_user(user)
    user.part_channel(channel)
    if not len(user.channels):
        event["server"].remove_user(user)

def handle_324(event):
    channel = event["server"].channels.get(event["args"][1])
    modes = event["args"][2]
    for mode in modes[1:]:
        if mode in event["server"].channel_modes:
            channel.add_mode(mode)

def handle_329(event):
    channel = event["server"].channels.get(event["args"][1])
    channel.creation_timestamp = int(event["args"][2])

def handle_477(timers, event):
    channel_name = event["server"].irc_lower(event["args"][1])
    if channel_name in event["server"].channels:
        key = event["server"].attempted_join[channel_name]
        timers.add("rejoin", 5, channel_name=channe_name, key=key,
            server_id=event["server"].id)

def kick(events, event):
    user = event["server"].get_user(event["prefix"].nickname)
    target = event["args"][1]
    channel = event["server"].channels.get(event["args"][0])
    reason = event["args"].get(2)
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
    old_name = event["args"][0]
    new_name = event["args"][1]
    channel = event["server"].channels.get(old_name)

    event["server"].channels.rename(old_name, new_name)
    events.on("received.rename").call(channel=channel, old_name=old_name,
        new_name=new_name, reason=event["args"].get(2), server=event["server"])
