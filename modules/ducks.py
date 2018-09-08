import random
from operator import itemgetter
from time import time

import Utils

DUCK_TAIL = "・゜゜・。。・゜゜"
DUCK_HEAD = ["\_o< ", "\_O< ", "\_0< ", "\_\u00f6< ", "\_\u00f8< ",
             "\_\u00f3< "]
DUCK_MESSAGE = ["QUACK!", "FLAP FLAP!", "quack!", "squawk!"]
DUCK_MESSAGE_RARE = ["beep boop!", "QUACK QUACK QUACK QUACK QUACK!!",
                     "HONK!", "I AM THE METAL DUCK"]

DUCK_MINIMUM_MESSAGES = 10
DUCK_MINIMUM_UNIQUE = 3

CHANNELS_ENABLED = []


class Module(object):

    def __init__(self, bot, events, exports):
        self.bot = bot
        self.events = events

        events.on("received").on("command").on("bef").hook(self.befriend,
                                                           priority=1,
                                                           help="Befriend a "
                                                                "duck!")
        events.on("received").on("command").on("bang").hook(self.shoot,
                                                            priority=1,
                                                            help="Shoot a "
                                                                 "duck! "
                                                                 "Meanie.",
                                                            )
        # events.on("received").on("command").on("decoy").hook(self.set_decoy,
        #                                                     help="Be a
        # sneaky fellow
        #                                                          and make a
        # decoy duck!")
        events.on("received").on("command").on("friends").hook(
            self.duck_friends,
            help="See who the friendliest people to ducks are!")
        events.on("received").on("command").on("killers").hook(
            self.duck_enemies,
            help="See who shoots the most smount of ducks!")
        events.on("received").on("command").on("duckstats").hook(
            self.duck_stats,
            help="Shows your duck stats!")

        exports.add("channelset", {"setting": "ducks-enabled",
                                   "help": "Toggle ducks!",
                                   "validate": Utils.bool_or_none})

        exports.add("channelset", {"setting": "ducks-kick",
                                   "help": "Should the bot kick if there's no "
                                           "duck?",
                                   "validate": Utils.bool_or_none})

        events.on("new.channel").hook(self.bootstrap)

        events.on("received").on("message").on("channel").hook(
            self.channel_message, priority=2)

    def bootstrap(self, event):
        channel = event["channel"]

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

        channel.games["ducks"] = {
            'messages': 0,
            'duck_spawned': 0,
            'unique_users': [],
            'next_duck_time': rand_time
        }

    def start_game(self, channel):
        #   event is immediately the IRCChannel.Channel() event for the current
        #   channel
        self.clear_ducks(channel)

    def generate_next_duck_time(self):
        rand_time = random.randint(int(time()) + 180, int(time()) + 960)
        return rand_time

    def is_duck_visible(self, event):
        channel = event["target"]

        visible = bool(channel.games["ducks"]["duck_spawned"])
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

    def should_generate_duck(self, event):
        channel = event["channel"]
        game = channel.games["ducks"]

        spawned = game["duck_spawned"]
        unique = len(game["unique_users"])
        messages = game["messages"]
        next_duck = game["next_duck_time"]

        # DUCK_MINIMUM_MESSAGES = 10
        # DUCK_MINIMUM_UNIQUE = 3

        if spawned == 0 and next_duck < time() and unique > \
                DUCK_MINIMUM_UNIQUE and \
                messages > \
                DUCK_MINIMUM_MESSAGES:
            return True
        else:
            return False

    def show_duck(self, event):
        channel = event["channel"]
        duck = ""

        if channel.games["ducks"]["duck_spawned"] == 1:
            return

        duck += DUCK_TAIL
        duck += random.choice(DUCK_HEAD)

        duck = str(Utils.color(4) + Utils.bold(duck + random.choice(
            DUCK_MESSAGE_RARE)) + Utils.color(4)) if 1 == random.randint(1,
                                                                         20) \
            else duck + random.choice(DUCK_MESSAGE)

        channel.send_message(duck)
        channel.games["ducks"]["duck_spawned"] = 1

    def channel_message(self, event):
        channel = event["channel"]

        if "ducks" not in channel.games.keys():
            return

        user = event["user"]
        game = channel.games["ducks"]

        if game["duck_spawned"] == 1 or channel.has_user(
                event["user"]) == False:
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
        print(channel)
        if self.is_duck_channel(channel) == False:
            return

        if self.is_duck_visible(event) == False:
            if self.should_kick(event):
                self.kick_bef(event)
            return

        channel.games["ducks"][
            "next_duck_time"] = self.generate_next_duck_time()
        channel.games["ducks"]["duck_spawned"] = 0

        total_befriended = channel.get_user_setting(uid, "ducks-befriended", 0)
        total_befriended = total_befriended + 1

        channel.set_user_setting(uid, "ducks-befriended", total_befriended)

        event["stdout"].write(
            "Aww! " + nick + " befriended a duck! You've befriended "
            + Utils.bold(
                str(
                    total_befriended)) + " ducks in " + Utils.bold(
                channel.name) + "!")

        self.clear_ducks(channel)

    def shoot(self, event):
        channel = event["target"]
        user = event["user"]
        nick = user.nickname
        uid = user.get_id()

        if self.is_duck_channel(channel) == False:
            return

        if self.is_duck_visible(event) == False:
            if self.should_kick(event):
                self.kick_bang(event)
            return

        channel.games["ducks"][
            "next_duck_time"] = self.generate_next_duck_time()
        channel.games["ducks"]["duck_spawned"] = 0

        total_shot = channel.get_user_setting(uid, "ducks-shot", 0)
        total_shot = total_shot + 1

        channel.set_user_setting(uid, "ducks-shot", total_shot)

        event["stdout"].write(
            "Pow! " + nick + " shot a duck! You've shot " + Utils.bold(
                str(
                    total_shot)) + " ducks in " + Utils.bold(
                channel.name) + "!")

        self.clear_ducks(channel)

    def duck_stats(self, event):
        user = event["user"]
        channel = event["target"].name
        nick = user.nickname
        id = user.get_id()

        poached = user.get_channel_settings_per_setting("ducks-shot", []
                                                        )
        friends = user.get_channel_settings_per_setting(
            "ducks-befriended", []
        )

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

        event["stdout"].write(
            nick + ": " + str(total_poached) + " ducks killed (" + str(
                channel_poached) + " in " + channel + "), and " + str(
                total_friends) + " ducks befriended (" + str(
                channel_friends)
            + " in " + channel + ")")

    def duck_enemies(self, event):
        the_enemy = event["server"].find_all_user_channel_settings(
            "ducks-shot")

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

        sentence = "Most Notorious Users -- "

        length = len(enemy_nicks) if len(enemy_nicks) < 11 else 11

        for i in range(0, length):
            sentence += enemy_nicks[i] + " (" + str(enemy_ducks[i]) + ")"
            if i < 10:
                sentence += ", "

        sentence = sentence[0:-2]

        event["stdout"].write(sentence)

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

        sentence = "Friendliest Users -- "

        length = len(friend_nicks) if len(friend_nicks) < 11 else 11

        for i in range(0, length):
            sentence += friend_nicks[i] + " (" + str(friend_ducks[i]) + ")"
            if i < 10:
                sentence += ", "

        sentence = sentence[0:-2]

        event["stdout"].write(sentence)
