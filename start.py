#!/usr/bin/env python3

import sys

if sys.version_info < (3, 6):
    sys.stderr.write("BitBot requires python 3.6.0 or later\n")
    sys.exit(1)

import argparse, faulthandler, os, platform, time
from src import Cache, Config, Database, EventManager, Exports, IRCBot
from src import Logging, ModuleManager, Timers, utils

faulthandler.enable()

directory = os.path.dirname(os.path.realpath(__file__))

arg_parser = argparse.ArgumentParser(
    description="Python3 event-driven modular IRC bot")

arg_parser.add_argument("--version", "-v", action="store_true")

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

arg_parser.add_argument("--verbose", "-V", action="store_true")
arg_parser.add_argument("--log-level", "-L")
arg_parser.add_argument("--no-logging", "-N", action="store_true")

arg_parser.add_argument("--module", "-m",
    help="Execute an action against a specific module")
arg_parser.add_argument("--module-args", "-M",
    help="Arguments to give in action against a specific module")

args = arg_parser.parse_args()

if args.version:
    print("BitBot %s" % IRCBot.VERSION)
    sys.exit(0)

log_level = args.log_level
if not log_level:
    log_level = "debug" if args.verbose else "info"

log = Logging.Log(not args.no_logging, log_level, args.log_dir)

log.info("Starting BitBot %s (Python v%s)",
    [IRCBot.VERSION, platform.python_version()])

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

if args.module:
    definition = modules.find_module(args.module)
    module = modules.load_module(bot, definition)
    module.module.command_line(args.module_args)
    sys.exit(0)


server_configs = bot.database.servers.get_all()

if len(server_configs):
    bot.load_modules()

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
