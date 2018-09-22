import random
from operator import itemgetter
from time import time
import EventManager

import Utils

DUCK_TAIL = "・゜゜・。。・゜゜"
DUCK_HEAD = ["\_o< ", "\_O< ", "\_0< ", "\_\u00f6< ", "\_\u00f8< ",
             "\_\u00f3< "]
DUCK_MESSAGE = ["QUACK!", "FLAP FLAP!", "quack!", "squawk!"]
DUCK_MESSAGE_RARE = ["beep boop!", "QUACK QUACK QUACK QUACK QUACK!!", "HONK!",
                     Utils.underline("I AM THE METAL DUCK")]

DUCK_MINIMUM_MESSAGES = 10
DUCK_MINIMUM_UNIQUE = 3


class Module(object):

    def __init__(self, bot, events, exports):
        self.bot = bot
        self.events = events

        events.on("received.command.bef").hook(self.befriend,
            priority=EventManager.PRIORITY_HIGH,
            help="Befriend a duck!")
        events.on("received.command.bang").hook(self.shoot,
            priority=EventManager.PRIORITY_HIGH,
            help="Shoot a duck! Meanie.")
        events.on("received.command.decoy").hook(
            self.duck_decoy,
            priority=EventManager.PRIORITY_HIGH,
            help="Lay out a sneaky decoy!")


        events.on("received.command.friends").hook(self.duck_friends,
            help="See who the friendliest people to ducks are!")
        events.on("received.command.killers").hook(self.duck_enemies,
            help="See who shoots the most smount of ducks!")
        events.on("received.command.duckstats").hook(self.duck_stats,
            help="Shows your duck stats!")

        exports.add("channelset", {"setting": "ducks-enabled",
            "help": "Toggle ducks!", "validate": Utils.bool_or_none})

        exports.add("channelset", {"setting": "ducks-kick",
            "help": "Should the bot kick if there's no duck?",
             "validate": Utils.bool_or_none})

        exports.add("channelset", {"setting": "ducks-min-unique",
                                   "help": "Minimum unique users required to "
                                           "talk before a duck spawns.",
                                   "validate": Utils.int_or_none})

        exports.add("channelset", {"setting": "ducks-min-messages",
                                   "help": "Minimum messages between ducks "
                                           "spawning.",
                                   "validate": Utils.int_or_none})

        events.on("new.channel").hook(self.new_channel)

        events.on("received.message.channel").hook(
            self.channel_message, EventManager.PRIORITY_LOW)

        for server in self.bot.servers.values():
            for channel in server.channels.values():
                self.bootstrap(channel)

    def new_channel(self, event):
        self.bootstrap(event["channel"])

    def bootstrap(self, channel):
        self.init_game_var(channel)
        # getset
        ducks_enabled = channel.get_setting("ducks-enabled", False)

        if ducks_enabled == True:
            self.start_game(channel)

    def is_duck_channel(self, channel):
        if channel.get_setting("ducks-enabled", False) == False:
            return False

        if hasattr(channel, 'games') == False:
            return False

        if "ducks" not in channel.games.keys():
            return False

        return True

    def init_game_var(self, channel):
        if hasattr(channel, 'games') == False:
            channel.games = {}

    def clear_ducks(self, channel):
        rand_time = self.generate_next_duck_time()

        del channel.games["ducks"]
        channel.games["ducks"] = {'messages': 0, 'duck_spawned': 0,
                                  'unique_users': [],
                                  'next_duck_time': rand_time,
                                  'decoy_spawned': 0, 'decoy_requested': 0,
                                  'next_decoy_time': rand_time}

    def start_game(self, channel):
        #   event is immediately the IRCChannel.Channel() event for the current
        #   channel
        self.clear_ducks(channel)

        min_unique = channel.get_setting("ducks-min-unique",
                                         0)
        min_messages = channel.get_setting("ducks-min-messages",
                                           0)

        if min_unique == 0:
            channel.set_setting("ducks-min-unique", DUCK_MINIMUM_UNIQUE)

        if min_messages == 0:
            channel.set_setting("ducks-min-messages", DUCK_MINIMUM_MESSAGES)

    def generate_next_duck_time(self):
        rand_time = random.randint(int(time()) + 1, int(time()) + 2)
        return rand_time

    def is_duck_visible(self, event, decoy=False):
        channel = event["target"]

        visible = channel.games["ducks"]["decoy_spawned"] if \
            decoy else channel.games["ducks"]["duck_spawned"]
        return visible

    def should_kick(self, event):
        channel = event["target"]

        return channel.get_setting("ducks-kick", False)

    def kick_bef(self, event):
        channel = event["target"]
        target = event["user"].nickname

        channel.send_kick(target,
                          "You tried befriending a non-existent duck. Creepy!")

    def kick_bang(self, event):
        channel = event["target"]
        target = event["user"].nickname

        channel.send_kick(target,
                          "You tried shooting a non-existent duck. Creepy!")

    def duck_decoy(self, event):
        channel = event["target"]
        if self.is_duck_channel(channel) == False:
            return

        if self.is_duck_visible(event):
            return

        game = channel.games["ducks"]
        game["decoy_requested"] = 1

        event.eat()


    def should_generate_duck(self, event):
        channel = event["channel"]
        game = channel.games["ducks"]

        spawned = int(game["decoy_spawned"] or game["duck_spawned"])
        decoy = bool(game["decoy_requested"])
        unique = len(game["unique_users"])
        messages = game["messages"]
        next_duck = game["next_decoy_time"] if decoy else game["next_duck_time"]

        min_unique = 1 if decoy else channel.get_setting("ducks-min-unique",
                                          DUCK_MINIMUM_UNIQUE)
        min_messages = channel.get_setting("ducks-min-messages", DUCK_MINIMUM_MESSAGES)

        requirement = (unique >= min_unique and messages >= min_messages)

        # DUCK_MINIMUM_MESSAGES = 10
        # DUCK_MINIMUM_UNIQUE = 3

        if spawned == 0 and next_duck < time():
            if requirement:
                return True
            else:
                return False
        else:
            return False

    def show_duck(self, event):
        channel = event["channel"]
        game = channel.games["ducks"]
        duck = ""

        if game["duck_spawned"] == 1 or game["decoy_spawned"] == 1:
            return

        duck += DUCK_TAIL
        duck += random.choice(DUCK_HEAD)

        if random.randint(1, 20) == 1:
            # rare!
            message = random.choice(DUCK_MESSAGE_RARE)
            duck = Utils.color(Utils.bold(duck + message), Utils.COLOR_RED)
        else:
            # not rare!
            duck += random.choice(DUCK_MESSAGE)

        channel.send_message(duck)

        # Decoys take priority over regular ducks.
        if game["decoy_requested"] == 1:
            game["decoy_spawned"] = 1
            game["decoy_requested"] = 0

            game["next_duck_time"] = self.generate_next_duck_time()
        else:
            game["duck_spawned"] = 1

    def channel_message(self, event):
        if not event["channel"].get_setting("ducks-enabled", False):
            return
        channel = event["channel"]

        if "ducks" not in channel.games.keys():
            return

        user = event["user"]
        game = channel.games["ducks"]

        if game["decoy_spawned"] == 1 or game["duck_spawned"] == 1 or \
                channel.has_user(event["user"]) == False:
            return

        unique = game["unique_users"]
        messages = game["messages"]

        if user not in unique:
            game["unique_users"].append(user)
            messages_increment = 1
        else:
            messages_increment = 0.5

        game["messages"] = messages + messages_increment

        if self.should_generate_duck(event) == True:
            self.show_duck(event)

    def befriend(self, event):
        channel = event["target"]
        user = event["user"]
        nick = user.nickname
        uid = user.get_id()
        if self.is_duck_channel(channel) == False:
            return

        if self.is_duck_visible(event, False) == False:
            if self.should_kick(event):
                self.kick_bef(event)
                event.eat()

            self.clear_ducks(channel)
            return

        channel.games["ducks"][
            "next_duck_time"] = self.generate_next_duck_time()
        channel.games["ducks"]["duck_spawned"] = 0

        total_befriended = channel.get_user_setting(uid, "ducks-befriended", 0)
        total_befriended = total_befriended + 1

        channel.set_user_setting(uid, "ducks-befriended", total_befriended)

        msg = "Aww! %s befriended a duck! You've befriended %s ducks in %s!" \
              % (Utils.bold(nick), Utils.bold(total_befriended),
                 Utils.bold(channel.name))

        event["stdout"].write(msg)

        self.clear_ducks(channel)
        event.eat()

    def shoot(self, event):
        channel = event["target"]
        user = event["user"]
        nick = user.nickname
        uid = user.get_id()

        if self.is_duck_channel(channel) == False:
            return

        if self.is_duck_visible(event, False) == False:
            if self.should_kick(event):
                self.kick_bang(event)
                event.eat()

            self.clear_ducks(channel)
            return

        channel.games["ducks"][
            "next_duck_time"] = self.generate_next_duck_time()
        channel.games["ducks"]["duck_spawned"] = 0

        total_shot = channel.get_user_setting(uid, "ducks-shot", 0)
        total_shot = total_shot + 1

        channel.set_user_setting(uid, "ducks-shot", total_shot)

        msg = "Pow! %s shot a duck! You've shot %s ducks in %s!" \
              % (Utils.bold(nick), Utils.bold(total_shot),
                 Utils.bold(channel.name))

        event["stdout"].write(msg)

        self.clear_ducks(channel)
        event.eat()

    def duck_stats(self, event):
        user = event["user"]
        channel = event["target"].name
        nick = user.nickname
        id = user.get_id()

        poached = user.get_channel_settings_per_setting("ducks-shot", [])
        friends = user.get_channel_settings_per_setting("ducks-befriended", [])

        channel_friends = 0
        channel_poached = 0

        total_friends = 0
        total_poached = 0

        for room, number in friends:
            if room == channel:
                channel_friends = number
                total_friends += number
            else:
                total_friends += number

        for room, number in poached:
            if room == channel:
                channel_poached = number
                total_poached += number
            else:
                total_poached += number

        tf = total_friends
        tp = total_poached
        cp = channel_poached
        cf = channel_friends

        msg = "%s ducks killed (%s in %s), and %s ducks befriended (%s in %s)" \
              % (Utils.bold(tp), Utils.bold(cp), Utils.bold(channel),
                 Utils.bold(tf), Utils.bold(cf), Utils.bold(channel))

        event["stdout"].write(Utils.bold(nick) + ": " + msg)
        event.eat()

    def duck_enemies(self, event):
        the_enemy = event["server"].find_all_user_channel_settings("ducks-shot")

        notorious = {}
        enemy_nicks = []
        enemy_ducks = []

        for i in the_enemy:
            if i[1] in notorious.keys():
                notorious[i[1]] += i[2]
            else:
                notorious[i[1]] = i[2]

        for user, enemies in sorted(notorious.items(), key=itemgetter(1),
                                    reverse=True):
            enemy_nicks.append(user)
            enemy_ducks.append(enemies)

        sentence = Utils.bold("Duck Wranglers: ")
        build = []

        length = len(enemy_nicks) if len(enemy_nicks) < 8 else 8

        for i in range(0, length):
            nick = Utils.prevent_highlight(enemy_nicks[i])
            build.append("%s (%s)" \
                         % (Utils.bold(nick),
                            enemy_ducks[i]))

        sentence += ", ".join(build)

        event["stdout"].write(sentence)
        event.eat()

    def duck_friends(self, event):
        friends = event["server"].find_all_user_channel_settings(
            "ducks-befriended")

        friendliest = {}
        friend_nicks = []
        friend_ducks = []

        for i in friends:
            if i[1] in friendliest.keys():
                friendliest[i[1]] += i[2]
            else:
                friendliest[i[1]] = i[2]

        for user, friends in sorted(friendliest.items(), key=itemgetter(1),
                                    reverse=True):
            friend_nicks.append(user)
            friend_ducks.append(friends)

        sentence = Utils.bold("Duck Friends: ")

        length = len(friend_nicks) if len(friend_nicks) < 8 else 8
        build = []

        for i in range(0, length):
            nick = Utils.prevent_highlight(friend_nicks[i])
            build.append("%s (%s)" \
                         % (Utils.bold(nick),
                            friend_ducks[i])
                         )

        sentence += ", ".join(build)

        event["stdout"].write(sentence)
        event.eat()
