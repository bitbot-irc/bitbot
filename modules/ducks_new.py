from operator import itemgetter
import Utils
import random

DUCK_TAIL = "・゜゜・。。・゜゜"
DUCK_HEAD = ["\_o< ", "\_O< ", "\_0< ", "\_\u00f6< ", "\_\u00f8< ",
             "\_\u00f3< "]
DUCK_MESSAGE = ["QUACK!", "FLAP FLAP!", "quack!", "squawk!"]
DUCK_MESSAGE_RARE = ["beep boop!", "QUACK QUACK QUACK QUACK QUACK!!", "HONK!"]

DELAY_REDUCE_UNIQUE = 1
DELAY_REDUCE = 0.5

CHANNELS_ENABLED = []


class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        self.events = events

        # events.on("received").on("command").on("bef").hook(self.duck_action,
        #                                       help="Befriend a duck!")
        # events.on("received").on("command").on("bang").hook(self.duck_bang,
        #                                        help="Shoot a duck! Meanie.")
        # events.on("received").on("command").on("decoy").hook(self.set_decoy,
        #                                         help="Be a sneaky fellow
        ## and make a decoy duck.")
        # events.on("received").on("command").on("friends").hook(
        #    self.duck_friends,
        #                                           help="See who the
        # friendliest people to ducks are!")
        # events.on("received").on("command").on("killers").hook(
        #    self.duck_enemies,
        #                                           help="See who shoots the
        # most amount of ducks.")
        # events.on("received").on("command").on("duckstats").hook(
        #   self.duck_stats,
        #                                            help="Shows your duck "
        #                                                 "stats!")

        exports.add("channelset", {"setting": "ducks-enabled",
                                   "help": "Toggle ducks!",
                                   "validate": Utils.bool_or_none})

        events.on("new.channel").hook(self.bootstrap)

        events.on("received").on("message").on("channel").hook(
            self.channel_message)

    def bootstrap(self, event):
        channel = event["channel"]
        print("Init for " + channel.name)
        self.init_game_var(channel)
        # getset
        ducks_enabled = channel.get_setting("ducks-enabled", False)

        print("Ducks enabled for " + channel.name + " -- " + str(
            ducks_enabled))
        if ducks_enabled == True:
            print("Starting game for " + channel.name)
            self.start_game(channel)

    def init_game_var(self, event):
        channel = event


        if hasattr(channel, 'games') == False:
            channel.games = {}


    def start_game(self, event):
        #   event is immediately the IRCChannel.Channel() event for the current
        #   channel

        channel = event

        print("Starting duck game for channel: " + channel.name)

        if "ducks" not in channel.games.keys():
            channel.games["ducks"] = {
                'current_active_delay': 10,
                'current_unique_nicks': 3,
                'duck_spawned': 0,
                'unique_nicks': []
            }

        print(channel.games)


    def channel_message(self, event):
        channel = event["channel"]
        channel_name = channel.name

        if "ducks" not in channel.games.keys():
            return

        user = event["user"]
        hostname = user.hostname
        game = channel.games["ducks"]

        if hostname not in game["unique_nicks"]:
            game["unique_nicks"].append(hostname)

            if game["current_unique_nicks"] > 0:
                game["current_unique_nicks"] = game["current_unique_nicks"] - 1

            if game["current_active_delay"] > 0:
                game["current_active_delay"] = game["current_active_delay"] \
                                               - DELAY_REDUCE_UNIQUE
        else:
            if game["current_active_delay"] > 0:
                game["current_active_delay"] = game["current_active_delay"] \
                - DELAY_REDUCE
