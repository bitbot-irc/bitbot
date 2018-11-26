#!/usr/bin/env python3

import argparse, os, sys, time
from src import Cache, Config, Database, EventManager, Exports, IRCBot
from src import Logging, ModuleManager, Timers, utils

directory = os.path.dirname(os.path.realpath(__file__))

arg_parser = argparse.ArgumentParser(
    description="Python3 event-driven modular IRC bot")

arg_parser.add_argument("--config", "-c",
    help="Location of the JSON config file",
    default=os.path.join(directory, "bot.conf"))

arg_parser.add_argument("--database", "-d",
    help="Location of the sqlite3 database file",
    default=os.path.join(directory, "databases", "bot.db"))

arg_parser.add_argument("--log-dir", "-l",
    help="Location of the log directory",
    default=os.path.join(directory, "logs"))

arg_parser.add_argument("--add-server", "-a",
    help="Add a new server", action="store_true")

arg_parser.add_argument("--verbose", "-v", action="store_true")

args = arg_parser.parse_args()

log_level = "debug" if args.verbose else "info"
log = Logging.Log(log_level, args.log_dir)
database = Database.Database(log, args.database)

if args.add_server:
    print("Adding a new server")
    utils.cli.add_server(database)
    sys.exit(0)

cache = Cache.Cache()
config = Config.Config(args.config)
events = events = EventManager.EventHook(log)
exports = exports = Exports.Exports()
timers = Timers.Timers(database, events, log)
modules = modules = ModuleManager.ModuleManager(events, exports, timers, config,
    log, os.path.join(directory, "modules"))

bot = IRCBot.Bot(directory, args, cache, config, database, events,
    exports, log, modules, timers)

whitelist = bot.get_setting("module-whitelist", [])
blacklist = bot.get_setting("module-blacklist", [])

server_configs = bot.database.servers.get_all()
if len(server_configs):
    modules.load_modules(bot, whitelist=whitelist, blacklist=blacklist)

    servers = []
    for server_id, alias in server_configs:
        server = bot.add_server(server_id, connect=False)
        if not server == None and server.get_setting("connect", True):
            servers.append(server)

    bot._events.on("boot.done").call()

    timers.setup(bot.find_settings_prefix("timer-"))

    for server in servers:
        if not bot.connect(server):
            sys.stderr.write("failed to connect to '%s', exiting\r\n" % (
                str(server)))
            sys.exit(1)

    try:
        bot.run()
    except Exception as e:
        log.critical("Unhandled exception: %s", [str(e)], exc_info=True)
        sys.exit(1)
else:
    try:
        if utils.cli.bool_input("no servers found, add one?"):
            utils.cli.add_server(database)
    except KeyboardInterrupt:
        print()
        pass
