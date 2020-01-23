from src import utils

def handle_311(event):
    nickname = event["line"].args[1]
    username = event["line"].args[2]
    hostname = event["line"].args[3]
    realname = event["line"].args[4]

    if event["server"].is_own_nickname(nickname):
        event["server"].username = username
        event["server"].hostname = hostname
        event["server"].realname = realname

    target = event["server"].get_user(nickname)
    target.username = username
    target.hostname = hostname
    target.realname = realname

def quit(events, event):
    nickname = None
    if event["direction"] == utils.Direction.Recv:
        nickname = event["line"].source.nickname
    reason = event["line"].args.get(0)

    if event["direction"] == utils.Direction.Recv:
        nickname = event["line"].source.nickname
        if (not event["server"].is_own_nickname(nickname) and
                not event["line"].source.hostmask == "*"):
            user = event["server"].get_user(nickname)
            events.on("received.quit").call(reason=reason, user=user,
                server=event["server"])
            event["server"].remove_user(user)
        else:
            event["server"].disconnect()
    else:
        events.on("send.quit").call(reason=reason, server=event["server"])

def nick(events, event):
    new_nickname = event["line"].args.get(0)
    user = event["server"].get_user(event["line"].source.nickname)
    old_nickname = user.nickname
    user.set_nickname(new_nickname)
    event["server"].change_user_nickname(old_nickname, new_nickname)

    if not event["server"].is_own_nickname(event["line"].source.nickname):
        events.on("received.nick").call(new_nickname=new_nickname,
            old_nickname=old_nickname, user=user, server=event["server"])
    else:
        event["server"].set_own_nickname(new_nickname)
        events.on("self.nick").call(server=event["server"],
            new_nickname=new_nickname, old_nickname=old_nickname)

def away(events, event):
    user = event["server"].get_user(event["line"].source.nickname)
    message = event["line"].args.get(0)
    if message:
        user.away = True
        user.away_message = message
        events.on("received.away.on").call(user=user, server=event["server"],
            message=message)
    else:
        user.away = False
        user.away_message = None
        events.on("received.away.off").call(user=user, server=event["server"])

def chghost(events, event):
    nickname = event["line"].source.nickname
    username = event["line"].args[0]
    hostname = event["line"].args[1]

    if event["server"].is_own_nickname(nickname):
        event["server"].username = username
        event["server"].hostname = hostname

    target = event["server"].get_user(nickname)
    events.on("received.chghost").call(user=target, server=event["server"],
        username=username, hostname=hostname)

    target.username = username
    target.hostname = hostname

def setname(event):
    nickname = event["line"].source.nickname
    realname = event["line"].args[0]

    user = event["server"].get_user(nickname)
    user.realname = realname

    if event["server"].is_own_nickname(nickname):
        event["server"].realname = realname

def account(events, event):
    user = event["server"].get_user(event["line"].source.nickname)

    if not event["line"].args[0] == "*":
        user.account = event["line"].args[0]
        events.on("received.account.login").call(user=user,
            server=event["server"], account=event["line"].args[0])
    else:
        user.account = None
        events.on("received.account.logout").call(user=user,
            server=event["server"])
