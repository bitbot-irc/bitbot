import typing
from src import IRCLine, utils

def user(username: str, realname: str) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("USER", [username, "0", "*", realname])
def nick(nickname: str) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("NICK", [nickname])

def capability_ls() -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("CAP", ["LS", "302"])
def capability_request(capability: str) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("CAP", ["REQ", capability])
def capability_end() -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("CAP", ["END"])
def authenticate(text: str) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("AUTHENTICATE", [text])

def password(password: str) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("PASS", [password])

def ping(nonce: str="hello") -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("PING", [nonce])
def pong(nonce: str="hello") -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("PONG", [nonce])

def join(channel_name: str, keys: typing.List[str]=None
        ) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("JOIN", [channel_name]+(
        keys if keys else []))
def part(channel_name: str, reason: str=None) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("PART", [channel_name]+(
        [reason] if reason else []))
def quit(reason: str=None) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("QUIT", [reason] if reason else [])

def privmsg(target: str, message: str, tags: typing.Dict[str, str]={}
        ) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("PRIVMSG", [target, message], tags=tags)
def notice(target: str, message: str, tags: typing.Dict[str, str]={}
        ) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("NOTICE", [target, message], tags=tags)
def tagmsg(target, tags: dict) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("TAGMSG", [target], tags=tags)

def mode(target: str, mode: str=None, args: typing.List[str]=None
        ) -> IRCLine.ParsedLine:
    command_args = [target]
    if mode:
        command_args.append(mode)
        if args:
            command_args = command_args+args
    return IRCLine.ParsedLine("MODE", command_args)

def topic(channel_name: str, topic: str) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("TOPIC", [channel_name, topic])
def kick(channel_name: str, target: str, reason: str=None
        ) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("KICK", [channel_name, target]+(
        [reason] if reason else []))
def names(channel_name: str) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("NAMES", [channel_name])
def list(search_for: str=None) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("LIST", [search_for] if search_for else [])
def invite(channel_name: str, target: str) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("INVITE", [target, channel_name])

def whois(target: str) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("WHOIS", [target])
def whowas(target: str, amount: int=None, server: str=None
        ) -> IRCLine.ParsedLine:
    command_args = [target]
    if amount:
        command_args.append(str(amount))
        if server:
            command_args.append(server)
    return IRCLine.ParsedLine("WHOWAS", command_args)
def who(filter: str=None) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("WHO", [filter] if filter else [])
def whox(mask: str, filter: str, fields: str, label: str=None
        ) -> IRCLine.ParsedLine:
    flags = "%s%%%s%s" % (filter, fields, ","+label if label else "")
    return IRCLine.ParsedLine("WHO", [mask, flags])

def batch_start(identifier: str, batch_type: str, tags: typing.Dict[str, str]={}
        ) -> IRCLine.ParsedLine:
    return IRCLine.ParsedLine("BATCH", ["+%s" % identifier, batch_type],
        tags=tags)

def batch_end(identifier: str, tags: typing.Dict[str, str]={}):
    return IRCLine.ParsedLine("BATCH", ["-%s" % identifier], tags=tags)
