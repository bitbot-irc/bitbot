from src import utils

def _from_self(server, source):
    if source:
        return server.is_own_nickname(source.nickname)
    else:
        return False

def message(events, event):
    from_self = _from_self(event["server"], event["line"].source)
    if from_self == None:
        return

    direction = "send" if from_self else "received"

    target_str = event["line"].args[0]

    message = None
    if len(event["line"].args) > 1:
        message = event["line"].args[1]

    if not from_self and (
            not event["line"].source or
            not event["server"].name or
            event["line"].source.hostmask == event["server"].name or
            target_str == "*"):
        if event["line"].source:
            event["server"].name = event["line"].source.hostmask

        events.on("received.server-notice").call(message=message,
            message_split=message.split(" "), server=event["server"])
        return

    if from_self:
        user = event["server"].get_user(event["server"].nickname)
    else:
        user = event["server"].get_user(event["line"].source.nickname)

    # strip prefix_symbols from the start of target, for when people use
    # e.g. 'PRIVMSG +#channel :hi' which would send a message to only
    # voiced-or-above users
    target = target_str.lstrip("".join(event["server"].statusmsg))

    is_channel = event["server"].is_channel(target)

    if is_channel:
        if not target in event["server"].channels:
            return
        target_obj = event["server"].channels.get(target)
    else:
        target_obj = event["server"].get_user(target)

    kwargs = {"server": event["server"], "target": target_obj,
        "target_str": target_str, "user": user, "tags": event["line"].tags,
        "is_channel": is_channel, "from_self": from_self, "line": event["line"]}

    action = False

    if message:
        ctcp_message = utils.irc.parse_ctcp(message)

        if ctcp_message:
            if (not ctcp_message.command == "ACTION" or not
                    event["line"].command == "PRIVMSG"):
                if event["line"].command == "PRIVMSG":
                    ctcp_action = "request"
                else:
                    ctcp_action = "response"
                events.on(direction).on("ctcp").on(ctcp_action).call(
                    message=ctcp_message.message, **kwargs)
                events.on(direction).on("ctcp").on(ctcp_action).on(
                    ctcp_message.command).call(message=ctcp_message.message,
                    **kwargs)
                return
            else:
                message = ctcp_message.message
                action = True

    if not message == None:
        kwargs["message"] = message
        kwargs["message_split"] = message.split(" ")
        kwargs["action"] = action

    event_type = event["line"].command.lower()
    if event_type == "privmsg":
        event_type = "message"

    context = "channel" if is_channel else "private"
    hook = events.on(direction).on(event_type).on(context)

    if is_channel:
        hook.call(channel=target_obj, **kwargs)
        if message:
            target_obj.buffer.add_message(user.nickname, message, action,
                event["line"].tags, from_self)
    else:
        hook.call(**kwargs)

        buffer_obj = target_obj
        if not from_self:
            buffer_obj = user

        if message:
            buffer_obj.buffer.add_message(user.nickname, message, action,
                event["line"].tags, from_self)
