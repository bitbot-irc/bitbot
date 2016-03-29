#!/usr/bin/env python3

import argparse
import IRCBot, Config, Database

def bool_input(s):
    result = input("%s (Y/n): " % s)
    return not result or result[0].lower() in ["", "y"]

bot = IRCBot.Bot()
database = Database.Database(bot)
config_object = Config.Config(bot)
bot.database = database
bot.config_object = config_object

servers = database.get_servers()
for server in servers:
    bot.add_server(*server)
if len(bot.servers):
    bot.modules.load_modules()
    bot.events.on("boot").on("done").call()
    bot.connect_all()
    bot.run()
else:
    try:
        if bool_input("no servers found, add one?"):
            hostname = input("hostname: ")
            port = int(input("port: "))
            tls = bool_input("tls?")
            password = input("password?: ")
            ipv4 = bool_input("ipv4?")
            nickname = input("nickname: ")
            username = input("username: ")
            realname = input("realname: ")
            database.add_server(hostname, port, password, ipv4,
                tls, nickname, username, realname)
    except KeyboardInterrupt:
        print()
        pass
