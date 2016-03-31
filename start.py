#!/usr/bin/env python3

import argparse, time
import IRCBot, Config, Database

def bool_input(s):
    result = input("%s (Y/n): " % s)
    return not result or result[0].lower() in ["", "y"]

arg_parser = argparse.ArgumentParser(
    description="Python3 event-driven asynchronous modular IRC bot")
arg_parser.add_argument("--config", "-c", default="bot.json",
    help="Location of the JSON config file")
arg_parser.add_argument("--database", "-d", default="bot.db",
    help="Location of the sqlite3 database file")
args = arg_parser.parse_args()

bot = IRCBot.Bot()
database = Database.Database(bot, args.database)
config_object = Config.Config(bot, args.config)
bot.database = database
bot.config_object = config_object

servers = database.get_servers()
for server in servers:
    bot.add_server(*server)
if len(bot.servers):
    bot.modules.load_modules()
    bot.events.on("boot").on("done").call()
    time.sleep(5)
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
