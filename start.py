#!/usr/bin/env python3

import argparse, os, sys, time
from src import Config, Database, EventManager, Exports, IRCBot
from src import IRCLineHandler, Logging, ModuleManager, Timers

def bool_input(s):
    result = input("%s (Y/n): " % s)
    return not result or result[0].lower() in ["", "y"]

directory = os.path.dirname(os.path.realpath(__file__))

arg_parser = argparse.ArgumentParser(
    description="Python3 event-driven modular IRC bot")

arg_parser.add_argument("--config", "-c",
    help="Location of the JSON config file",
    default=os.path.join(directory, "bot.conf"))

arg_parser.add_argument("--database", "-d",
    help="Location of the sqlite3 database file",
    default=os.path.join(directory, "databases", "bot.db"))

arg_parser.add_argument("--log", "-l",
    help="Location of the main log file",
    default=os.path.join(directory, "logs", "bot.log"))

arg_parser.add_argument("--verbose", "-v", action="store_true")

args = arg_parser.parse_args()


log = Logging.Log(args.log)
config = Config.Config(args.config)
database = Database.Database(log, args.database)
events = events = EventManager.EventHook(log)
exports = exports = Exports.Exports()
timers = Timers.Timers(database, events, log)
line_handler = IRCLineHandler.LineHandler(events, timers)
modules = modules = ModuleManager.ModuleManager(events, exports, config, log,
    os.path.join(directory, "modules"))

bot = IRCBot.Bot(args, config, database, events, exports, line_handler, log,
    modules, timers)

whitelist = bot.get_setting("module-whitelist", [])
blacklist = bot.get_setting("module-blacklist", [])
modules.load_modules(bot, whitelist=whitelist, blacklist=blacklist)

servers = []
for server_id, alias in bot.database.servers.get_all():
    server = bot.add_server(server_id, connect=False)
    if not server == None:
        servers.append(server)
if len(servers):
    bot._events.on("boot.done").call()

    bot.timers.setup(bot.find_settings_prefix("timer-"))

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
