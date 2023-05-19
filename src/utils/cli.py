from . import irc

def bool_input(s: str):
    result = input("%s (Y/n): " % s)
    return not result or result[0].lower() in ["", "y"]

def add_server():
    alias = input("alias (display name): ")
    hostname = input("hostname (address of server): ")
    port = int(input("port: "))
    tls = bool_input("tls?")
    password = input("password (optional, leave blank to skip): ")
    nickname = input("nickname: ")
    username = input("username (optional): ")
    realname = input("realname (optional): ")
    bindhost = input("bindhost (optional): ")

    return irc.IRCConnectionParameters(-1, alias, hostname, port, password, tls,
        bindhost, nickname, username, realname)
