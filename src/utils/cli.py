from src import Database

def bool_input(s: str):
    result = input("%s (Y/n): " % s)
    return not result or result[0].lower() in ["", "y"]

def add_server(database: "Database.Database"):
    alias = input("alias: ")
    hostname = input("hostname: ")
    port = int(input("port: "))
    tls = bool_input("tls?")
    password = input("password?: ")
    nickname = input("nickname: ")
    username = input("username: ")
    realname = input("realname: ")
    bindhost = input("bindhost?: ")

    server_id = database.servers.add(alias, hostname, port, password, tls,
        bindhost, nickname, username, realname)
