from . import irc

def bool_input(s: str):
    result = input("%s (Y/n): " % s)
    return not result or result[0].lower() in ["", "y"]

def add_server():
    alias = input("alias: ")
    hostname = input("hostname: ")
    port = int(input("port: "))
    tls = bool_input("tls?")
    password = input("password?: ")
    nickname = input("nickname: ")
    username = input("username: ")
    realname = input("realname: ")
    bindhost = input("bindhost?: ")

    return irc.IRCConnectionParameters(-1, alias, hostname, port, password, tls,
        bindhost, nickname, username, realname)
