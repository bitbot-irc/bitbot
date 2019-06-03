from src import utils

def _from_self(server, direction, prefix):
    if direction == utils.Direction.Send:
        if server.has_capability_str("echo-message"):
            return None
        else:
            return True
    else:
        if prefix:
            return server.is_own_nickname(prefix.nickname)
        else:
            return False

def message(events, event):
    from_self = _from_self(event["server"], event["direction"],
        event.get("prefix", None))
    if from_self == None:
        return

    target_str = event["args"][0]

    message = None
    if len(event["args"]) > 1:
        message = event["args"][1]

    if not from_self and (
            not event["prefix"] or
            not event["server"].name or
            event["prefix"].hostmask == event["server"].name or
            target_str == "*"):
        if event["prefix"]:
            event["server"].name = event["prefix"].hostmask

        events.on("received.server-notice").call(message=message,
            message_split=message.split(" "), server=event["server"])
        return

    if from_self:
        user = event["server"].get_user(event["server"].nickname)
    else:
        user = event["server"].get_user(event["prefix"].nickname)

    # strip prefix_symbols from the start of target, for when people use
    # e.g. 'PRIVMSG +#channel :hi' which would send a message to only
    # voiced-or-above users
    target = target_str.lstrip("".join(event["server"].prefix_symbols.keys()))

    is_channel = False

    if target[0] in event["server"].channel_types:
        is_channel = True
        if not target in event["server"].channels:
            return
        target_obj = event["server"].channels.get(target)
    else:
        target_obj = event["server"].get_user(target)

    kwargs = {"server": event["server"], "target": target_obj,
        "target_str": target_str, "user": user, "tags": event["tags"]}

    action = False

    if message:
        ctcp_message = utils.irc.parse_ctcp(message)

        if ctcp_message:
            if not ctcp_message.command == "ACTION" or not event["command"
                    ] == "PRIVMSG":
                if event["command"] == "PRIVMSG":
                    direction = "request"
                else:
                    direction = "response"
                events.on("received.ctcp").on(direction).on(ctcp_message.command
                    ).call(message=ctcp_message.message, **kwargs)
                return
            else:
                message = ctcp_message.message
                action = True

    if not message == None:
        kwargs["message"] = message
        kwargs["message_split"] = message.split(" ")
        kwargs["action"] = action

    event_type = event["command"].lower()
    if event["command"] == "PRIVMSG":
        event_type = "message"

    direction = "send" if from_self else "received"
    context = "channel" if is_channel else "private"
    hook = events.on(direction).on(event_type).on(context)

    if is_channel:
        hook.call(channel=target_obj, **kwargs)
        target_obj.buffer.add_message(user.nickname, message, action,
            event["tags"], from_self)
    else:
        hook.call(**kwargs)
        target_obj.buffer.add_message(user.nickname, message, action,
            event["tags"], True)
