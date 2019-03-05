from src import utils

def handle_311(event):
    nickname = event["args"][1]
    username = event["args"][2]
    hostname = event["args"][3]
    realname = event["args"][4]

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
    if event["direction"] == utils.Direction.RECV:
        nickname = event["prefix"].nickname
    reason = event["args"].get(0)

    if event["direction"] == utils.Direction.RECV:
        nickname = event["prefix"].nickname
        if (not event["server"].is_own_nickname(nickname) and
                not event["prefix"].hostmask == "*"):
            user = event["server"].get_user(nickname)
            event["server"].remove_user(user)
            events.on("received.quit").call(reason=reason, user=user,
                server=event["server"])
        else:
            event["server"].disconnect()
    else:
        events.on("send.quit").call(reason=reason, server=event["server"])

def nick(events, event):
    new_nickname = event["args"].get(0)
    user = event["server"].get_user(event["prefix"].nickname)
    old_nickname = user.nickname

    if not event["server"].is_own_nickname(event["prefix"].nickname):
        events.on("received.nick").call(new_nickname=new_nickname,
            old_nickname=old_nickname, user=user, server=event["server"])
    else:
        event["server"].set_own_nickname(new_nickname)
        events.on("self.nick").call(server=event["server"],
            new_nickname=new_nickname, old_nickname=old_nickname)

    user.set_nickname(new_nickname)
    event["server"].change_user_nickname(old_nickname, new_nickname)

def away(events, event):
    user = event["server"].get_user(event["prefix"].nickname)
    message = event["args"].get(0)
    if message:
        user.away = True
        user.away_message = message
        events.on("received.away.on").call(user=user, server=event["server"],
            message=message)
    else:
        user.away = False
        user.away_message = None
        events.on("received.away.off").call(user=user, server=event["server"])

def chghost(event):
    nickname = event["prefix"].nickname
    username = event["args"][0]
    hostname = event["args"][1]

    if event["server"].is_own_nickname(nickname):
        event["server"].username = username
        event["server"].hostname = hostname

    target = event["server"].get_user(nickname)
    target.username = username
    target.hostname = hostname

def setname(event):
    user = event["server"].get_user(event["prefix"].nickname)
    user.realname = event["args"][0]

def account(events, event):
    user = event["server"].get_user(event["prefix"].nickname)

    if not event["args"][0] == "*":
        user.identified_account = event["args"][0]
        user.identified_account_id = event["server"].get_user(
            event["args"][0]).get_id()
        events.on("received.account.login").call(user=user,
            server=event["server"], account=event["args"][0])
    else:
        user.identified_account = None
        user.identified_account_id = None
        events.on("received.account.logout").call(user=user,
            server=event["server"])
