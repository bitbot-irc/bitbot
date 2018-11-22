import random
from operator import itemgetter
from time import time
from src import EventManager, ModuleManager, utils

DUCK_TAIL = "・゜゜・。。・゜゜"
DUCK_HEAD = ["\_o< ", "\_O< ", "\_0< ", "\_\u00f6< ", "\_\u00f8< ",
             "\_\u00f3< "]
DUCK_MESSAGE = ["QUACK!", "FLAP FLAP!", "quack!", "squawk!"]
DUCK_MESSAGE_RARE = ["beep boop!", "QUACK QUACK QUACK QUACK QUACK!!", "HONK!"]

DUCK_MINIMUM_MESSAGES = 10
DUCK_MINIMUM_UNIQUE = 3

@utils.export("channelset", {"setting": "ducks-enabled",
    "help": "Toggle ducks!", "validate": utils.bool_or_none})
@utils.export("channelset", {"setting": "ducks-kick",
    "help": "Should the bot kick if there's no duck?",
    "validate": utils.bool_or_none})
@utils.export("channelset", {"setting": "ducks-min-unique",
    "help": "Minimum unique users required to talk before a duck spawns.",
     "validate": utils.int_or_none})
@utils.export("channelset", {"setting": "ducks-min-messages",
    "help": "Minimum messages between ducks spawning.",
    "validate": utils.int_or_none})
class Module(ModuleManager.BaseModule):
    def on_load(self):
        for server in self.bot.servers.values():
            for channel in server.channels.values():
                self.bootstrap(channel)

    @utils.hook("new.channel")
    def new_channel(self, event):
        self.bootstrap(event["channel"])

    def bootstrap(self, channel):
        self.init_game_var(channel)
        # getset
        ducks_enabled = channel.get_setting("ducks-enabled", False)

        if ducks_enabled:
            self.start_game(channel)

    def is_duck_channel(self, channel):
        if not channel.get_setting("ducks-enabled", False):
            return False

        if not hasattr(channel, 'games'):
            return False

        if "ducks" not in channel.games.keys():
            return False

        return True

    def init_game_var(self, channel):
        if not hasattr(channel, 'games'):
            channel.games = {}

    def clear_ducks(self, channel):
        rand_time = self.generate_next_duck_time()

        if hasattr(channel.games, "ducks"):
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

        min_unique = channel.get_setting("ducks-min-unique", 0)
        min_messages = channel.get_setting("ducks-min-messages", 0)

        if min_unique == 0:
            channel.set_setting("ducks-min-unique", DUCK_MINIMUM_UNIQUE)

        if min_messages == 0:
            channel.set_setting("ducks-min-messages", DUCK_MINIMUM_MESSAGES)

    def generate_next_duck_time(self):
        rand_time = random.randint(int(time()) + 360, int(time()) + 1200)
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

    @utils.hook("received.command.decoy")
    def duck_decoy(self, event):
        """
        :help: Prepare a decoy duck
        """
        channel = event["target"]
        if not self.is_duck_channel(channel):
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
            return bool(requirement)
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
            duck = utils.irc.color(utils.irc.bold(duck + message),
                utils.consts.RED)
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

    @utils.hook("received.message.channel",
        priority=EventManager.PRIORITY_MONITOR)
    def channel_message(self, event):
        if not event["channel"].get_setting("ducks-enabled", False):
            return
        channel = event["channel"]

        if "ducks" not in channel.games.keys():
            return

        user = event["user"]
        game = channel.games["ducks"]

        if game["decoy_spawned"] == 1 or game["duck_spawned"] == 1 or \
                not channel.has_user(event["user"]):
            return

        unique = game["unique_users"]
        messages = game["messages"]

        if user not in unique:
            game["unique_users"].append(user)
            messages_increment = 1
        else:
            messages_increment = 0.5

        game["messages"] = messages + messages_increment

        if self.should_generate_duck(event):
            self.show_duck(event)

    @utils.hook("received.command.bef")
    def befriend(self, event):
        """
        :help: Befriend a duck
        """
        channel = event["target"]
        user = event["user"]
        nick = user.nickname
        uid = user.get_id()
        if not self.is_duck_channel(channel):
            return

        if not self.is_duck_visible(event, False):
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
              % (utils.irc.bold(nick), utils.irc.bold(total_befriended),
                 utils.irc.bold(channel.name))

        event["stdout"].write(msg)

        self.clear_ducks(channel)
        event.eat()

    @utils.hook("received.command.bang")
    def shoot(self, event):
        """
        :help: Shoot a duck
        """
        channel = event["target"]
        user = event["user"]
        nick = user.nickname
        uid = user.get_id()

        if not self.is_duck_channel(channel):
            return

        if not self.is_duck_visible(event, False):
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
              % (utils.irc.bold(nick), utils.irc.bold(total_shot),
                 utils.irc.bold(channel.name))

        event["stdout"].write(msg)

        self.clear_ducks(channel)
        event.eat()

    @utils.hook("received.command.duckstats")
    def duck_stats(self, event):
        """
        :help: Show your duck stats
        """
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
            % (utils.irc.bold(tp), utils.irc.bold(cp), utils.irc.bold(channel),
            utils.irc.bold(tf), utils.irc.bold(cf), utils.irc.bold(channel))

        event["stdout"].write(utils.irc.bold(nick) + ": " + msg)
        event.eat()

    @utils.hook("received.command.killers")
    def duck_enemies(self, event):
        """
        :help: Show the top duck shooters
        """
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

        sentence = utils.irc.bold("Duck Wranglers: ")
        build = []

        length = len(enemy_nicks) if len(enemy_nicks) < 8 else 8

        for i in range(0, length):
            nick = utils.prevent_highlight(enemy_nicks[i])
            build.append("%s (%s)" \
                         % (utils.irc.bold(nick),
                            enemy_ducks[i]))

        sentence += ", ".join(build)

        event["stdout"].write(sentence)
        event.eat()

    @utils.hook("received.command.friends")
    def duck_friends(self, event):
        """
        :help: Show the top duck friends
        """
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

        sentence = utils.irc.bold("Duck Friends: ")

        length = len(friend_nicks) if len(friend_nicks) < 8 else 8
        build = []

        for i in range(0, length):
            nick = utils.prevent_highlight(friend_nicks[i])
            build.append("%s (%s)" \
                         % (utils.irc.bold(nick),
                            friend_ducks[i])
                         )

        sentence += ", ".join(build)

        event["stdout"].write(sentence)
        event.eat()
