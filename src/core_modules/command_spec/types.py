from src.utils.parse import SpecTypeError
from src.utils.irc import hostmask_match, hostmask_parse

TYPES = {}
def _type(func):
    TYPES[func.__name__] = func

def _assert_args(args, type):
    if not args:
        raise SpecTypeError("No %s provided" % type)

@_type
def rchannel(server, channel, user, args):
    if channel:
        return channel, 0
    elif args:
        if args[0] in server.channels:
            return server.channels.get(args[0]), 1
        else:
            raise SpecTypeError("No such channel")
    else:
        raise SpecTypeError("No channel provided")

@_type
def channel(server, channel, user, args):
    _assert_args(args, "channel")
    if args[0] in server.channels:
        return server.channels.get(args[0]), 1
    else:
        raise SpecTypeError("No such channel")

@_type
def cuser(server, channel, user, args):
    _assert_args(args, "user")
    target_user = server.get_user(args[0], create=False)
    if target_user and channel.has_user(target_user):
        return target_user, 1
    else:
        raise SpecTypeError("That user is not in this channel")

@_type
def ruser(server, channel, user, args):
    if args:
        target_user = server.get_user(args[0], create=False)
        if target_user:
            return target_user, 1
        else:
            raise SpecTypeError("No such user")
    else:
        return user, 0

@_type
def user(server, channel, user, args):
    _assert_args(args, "user")
    target_user = server.get_user(args[0], create=False)
    if target_user:
        return target_user, 1
    else:
        raise SpecTypeError("No such user")

@_type
def ouser(server, channel, user, args):
    _assert_args(args, "user")
    if server.has_user_id(args[0]):
        return server.get_user(args[0], create=True), 1
    else:
        raise SpecTypeError("No such user")

@_type
def nuser(server, channel, user, args):
    _assert_args(args, "user")
    return server.get_user(args[0], create=True), 1

@_type
def cmask(server, channel, user, args):
    _assert_args(args, "mask")
    hostmask_obj = hostmask_parse(args[0])
    users = []
    for user in channel.users:
        if hostmask_match(user.hostmask(), hostmask_obj):
            users.append(user)
    if users:
        return users, 1
    else:
        raise SpecTypeError("No users found")

@_type
def lstring(server, channel, user, args):
    if args:
        return " ".join(args), len(args)
    else:
        last_message = (channel or user).buffer.get()
        if last_message:
            return last_message.message, 0
        else:
            raise SpecTypeError("No message found")

@_type
def channelonly(server, channel, user, args):
    if channel:
        return True, 0
    else:
        raise SpecTypeError("Command not valid in PM")
@_type
def privateonly(server, channel, user, args):
    if not channel:
        return True, 0
    else:
        raise SpecTypeError("Command not valid in channel")
