#!/usr/bin/env python3

import argparse, os, sys, time
from src import Config, Database, EventManager, Exports, IRCBot
from src import IRCLineHandler, Logging, ModuleManager

def bool_input(s):
    result = input("%s (Y/n): " % s)
    return not result or result[0].lower() in ["", "y"]

arg_parser = argparse.ArgumentParser(
    description="Python3 event-driven asynchronous modular IRC bot")
arg_parser.add_argument("--config", "-c", default="bot.conf",
    help="Location of the JSON config file")
arg_parser.add_argument("--database", "-d", default="bot.db",
    help="Location of the sqlite3 database file")
arg_parser.add_argument("--verbose", "-v", action="store_true")

args = arg_parser.parse_args()

directory = os.path.dirname(os.path.realpath(__file__))

bot = IRCBot.Bot()

bot._events = events = EventManager.EventHook(bot)
bot._exports = exports = Exports.Exports()
bot.modules = modules = ModuleManager.ModuleManager(bot, events, exports,
    os.path.join(directory, "modules"))
bot.line_handler = IRCLineHandler.LineHandler(bot, bot._events)
bot.log = Logging.Log(bot, directory, "bot.log")
bot.database = Database.Database(bot, directory, args.database)
bot.config = Config.Config(bot, directory, args.config).load_config()
bot.args = args

bot._events.on("timer.reconnect").hook(bot.reconnect)
bot._events.on("boot.done").hook(bot.setup_timers)

whitelist = bot.get_setting("module-whitelist", [])
blacklist = bot.get_setting("module-blacklist", [])
bot.modules.load_modules(whitelist=whitelist, blacklist=blacklist)

servers = []
for server_id, alias in bot.database.servers.get_all():
    server = bot.add_server(server_id, connect=False)
    if not server == None:
        servers.append(server)
if len(servers):
    bot._events.on("boot.done").call()
    for server in servers:
        if not bot.connect(server):
            sys.stderr.write("failed to connect to '%s', exiting\r\n" % (
                str(server)))
            sys.exit(1)
    bot.run()
else:
    try:
        if bool_input("no servers found, add one?"):
            alias = input("alias: ")
            hostname = input("hostname: ")
            port = int(input("port: "))
            tls = bool_input("tls?")
            password = input("password?: ")
            ipv4 = bool_input("ipv4?")
            nickname = input("nickname: ")
            username = input("username: ")
            realname = input("realname: ")
            bot.database.servers.add(alias, hostname, port, password, ipv4,
                tls, nickname, username, realname)
    except KeyboardInterrupt:
        print()
        pass
