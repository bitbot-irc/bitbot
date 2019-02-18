import typing
from src import utils

def user(username: str, realname: str) -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("USER", [username, "0", "*", realname])
def nick(nickname: str) -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("NICK", [nickname])

def capability_ls() -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("CAP", ["LS", "302"])
def capability_request(capability: str) -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("CAP", ["REQ", capability])
def capability_end() -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("CAP", ["END"])
def authenticate(text: str) -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("AUTHENTICATE", [text])

def password(password: str) -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("PASS", [password])

def ping(nonce: str="hello") -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("PING", [nonce])
def pong(nonce: str="hello") -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("PONG", [nonce])

def join(channel_name: str, keys: typing.List[str]=None
        ) -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("JOIN", [channel_name]+keys if keys else [])
def part(channel_name: str, reason: str=None) -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("PART", [channel_name]+(
        [reason] if reason else []))
def quit(reason: str=None) -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("QUIT", [reason] if reason else [])

def message(target: str, message: str, tags: dict=None
        ) -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("PRIVMSG", [target, message], tags=tags)
def notice(target: str, message: str, tags: dict=None
        ) -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("NOTICE", [target, message], tags=tags)
def tagmsg(target, tags: dict) -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("TAGMSG", [target], tags=tags)

def mode(target: str, mode: str=None, args: typing.List[str]=None
        ) -> 'utils.irc.IRCParsedLine':
    command_args = [target]
    if mode:
        command_args.append(mode)
        if args:
            command_args = command_args+args
    return utils.irc.IRCParsedLine("MODE", command_args)

def topic(channel_name: str, topic: str) -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("TOPIC", [channel_name, topic])
def kick(channel_name: str, target: str, reason: str=None
        ) -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("KICK", [channel_name, target]+(
        [reason] if reason else []))
def names(channel_name: str) -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("NAMES", [channel_name])
def list(search_for: str=None) -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("LIST", [search_for] if search_for else [])
def invite(target: str, channel_name: str) -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("INVITE", [target, channel_name])

def whois(target: str) -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("WHOIS", [target])
def whowas(target: str, amount: int=None, server: str=None
        ) -> 'utils.irc.IRCParsedLine':
    command_args = [target]
    if amount:
        command_args.append(str(amount))
        if server:
            command_args.append(server)
    return utils.irc.IRCParsedLine("WHOWAS", command_args)
def who(filter: str=None) -> 'utils.irc.IRCParsedLine':
    return utils.irc.IRCParsedLine("WHO", [filter] if filter else [])
def whox(mask: str, filter: str, fields: str, label: str=None
        ) -> 'utils.irc.IRCParsedLine':
    flags = "%s%%%s%s" % (filter, fields, ","+label if label else "")
    return utils.irc.IRCParsedLine("WHO", [mask, flags])

def batch_start(identifier: str, batch_type: str, tags: dict=None):
    return utils.irc.IRCParsedLine("BATCH", ["+%s" % identifier, batch_type],
        tags=tags)

def batch_end(identifier: str, tags: dict=None):
    return utils.irc.IRCParsedLine("BATCH", ["+%s" % identifier], tags=tags)
