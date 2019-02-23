from src import utils

def _from_self(server, direction, prefix):
    if direction == utils.Direction.SEND:
        if "echo-message" in server.agreed_capabilities:
            return None
        else:
            return True
    else:
        if prefix:
            return server.is_own_nickname(prefix.nickname)
        else:
            return False

def privmsg(events, event):
    from_self = _from_self(event["server"], event["direction"],
        event.get("prefix", None))
    if from_self == None:
        return

    user = None
    if "prefix" in event and not from_self:
        user = event["server"].get_user(event["prefix"].nickname)

    message = event["args"][1]
    target = event["args"][0]

    # strip prefix_symbols from the start of target, for when people use
    # e.g. 'PRIVMSG +#channel :hi' which would send a message to only
    # voiced-or-above users
    statusmsg = []
    while target[0] in event["server"].prefix_symbols.keys():
        statusmsg.append(target[0])
        target = target[1:]

    channel = None
    if target[0] in event["server"].channel_types:
        if not target in event["server"].channels:
            return
        channel = event["server"].channels.get(target)

    action = False
    event_type = "message"
    ctcp_message = utils.irc.parse_ctcp(message)
    if ctcp_message:
        message = ctcp_message.message
        event_type = "ctcp.%s" % ctcp_message.command
        if ctcp_message.command == "ACTION":
            action = True
            message = ctcp_message.message

    if user and "account" in event["tags"]:
        user.identified_account = event["tags"]["account"]
        user.identified_account_id = event["server"].get_user(
            event["tags"]["account"]).get_id()

    kwargs = {"message": message, "message_split": message.split(" "),
        "server": event["server"], "tags": event["tags"],
        "action": action}

    direction = "send" if from_self else "received"
    context = "channel" if channel else "private"
    hook = events.on(direction).on(event_type).on(context)

    user_nickname = None
    if user:
        user_nickname = None if from_self else user.nickname

    if channel:
        hook.call(user=user, channel=channel, statusmsg=statusmsg, **kwargs)
        channel.buffer.add_message(user_nickname, message, action,
            event["tags"], user==None)
    elif event["server"].is_own_nickname(target):
        hook.call(user=user, **kwargs)
        user.buffer.add_message(user_nickname, message, action,
            event["tags"], False)
    elif from_self:
        # a message we've sent to a user
        user = event["server"].get_user(target)
        hook.call(user=user, **kwargs)
        user.buffer.add_message(user_nickname, message, action,
            event["tags"], True)

def notice(events, event):
    from_self = _from_self(event["server"], event["direction"],
        event.get("prefix", None))
    if from_self == None:
        return

    message = event["args"][1]
    target = event["args"][0]

    if "prefix" in event and (
            not event["prefix"] or
            not event["server"].name or
            event["prefix"].hostmask == event["server"].name or
            target == "*"):
        if event["prefix"]:
            event["server"].name = event["prefix"].hostmask

        events.on("received.server-notice").call(message=message,
            message_split=message.split(" "), server=event["server"])
    else:
        user = None
        if "prefix" in event and not from_self:
            user = event["server"].get_user(event["prefix"].nickname)

        channel = None
        if target[0] in event["server"].channel_types:
            channel = event["server"].channels.get(target)

        direction = "send" if from_self else "received"
        context = "channel" if channel else "private"
        hook = events.on(direction).on("notice").on(context)

        user_nickname = None
        if user:
            user_nickname = None if from_self else user.nickname

        kwargs = {"message": message, "message_split": message.split(" "),
            "server": event["server"], "tags": event["tags"]}

        if channel:
            hook.call(user=user, channel=channel, **kwargs)
            channel.buffer.add_notice(user_nickname, message, event["tags"],
                user==None)
        elif event["server"].is_own_nickname(target):
            hook.call(user=user, **kwargs)
            user.buffer.add_notice(user_nickname, message, event["tags"],
                False)
        elif from_self:
            # a notice we've sent to a user
            user = event["server"].get_user(target)
            hook.call(user=user, **kwargs)
            user.buffer.add_notice(user_nickname, message, event["tags"],
                True)

# IRCv3 TAGMSG, used to send tags without any other information
@utils.hook("raw.received.tagmsg")
def tagmsg(events, event):
    from_self = _from_self(event["server"], event["direction"],
        event.get("prefix", None))
    if from_self == None:
        return

    user = None
    if "prefix" in event and not from_self:
        user = event["server"].get_user(event["prefix"].nickname)

    target = event["args"][0]
    channel = None
    if target[0] in event["server"].channel_types:
        channel = event["server"].channels.get(target)

    direction = "send" if from_self else "received"
    context = "channel" if channel else "private"
    hook = events.on(direction).on("tagmsg").on(context)

    kwargs = {"server": event["server"], "tags": event["tags"]}

    if channel:
        hook.call(user=user, channel=channel, **kwargs)
    elif event["server"].is_own_nickname(target):
        hook.call(user=user, **kwargs)
    elif from_self:
        user = event["server"].get_user(target)
        hook.call(user=user, **kwargs)
