from operator import itemgetter
from threading import Timer
import Utils
import random

DUCK_LIST = [
    "・゜゜・。。・゜ ​ ゜\_O​< q​uack!",
    "・゜゜・。。・゜ ​ ゜\_o< QUACK!",
    "・゜゜・。 ​ 。・゜゜\​_ó< qu​ack!",
    "・゜゜・。 ​ 。・゜゜\​_ó< qu​ack quack!",
    "・゜゜ 。 ​ 。・゜  \​_ó< bawk!",
    "・゜゜ 。 ​ 。・゜゜\​_ó< squawk!",
    "・ ゜・。 ​ 。・゜゜ \​_ó< beep beep!"
]

class Module(object):
    def __init__(self, bot, events):
        self.bot = bot

        events.on("received.command.bef").hook(self.duck_bef,
                                               help="Befriend a duck!")
        events.on("received.command.bang").hook(self.duck_bang,
                                                help="Shoot a duck! Meanie.")
        events.on("received.command.decoy").hook(self.set_decoy,
                                                 help="Be a sneaky fellow and make a decoy duck.")
        events.on("received.command.friends").hook(self.duck_friends,
                                                   help="See who the friendliest people to ducks are!")
        events.on("received.command.killers").hook(self.duck_enemies,
                                                     help="See who shoots the most amount of ducks.")
        # events.on("received.command.ducks").hook(self.duck_list,
        #                                              help="Shows a list of the most popular duck superstars.")


        events.on("postboot").on("configure").on(
            "channelset").assure_call(setting="ducks-enabled",
                                      help="Toggles ducks!",
                                      validate=Utils.bool_or_none)

        events.on("received.numeric.366").hook(self.bootstrap)

        events.on("raw").on("376").hook(self.duck_loop_entry)

        events.on("timer").on("duck-decoy").hook(self.duck_decoy)
        events.on("timer").on("show-duck").hook(self.show_duck)

    def duck_loop_entry(self, event):
        wait = self.get_random_duck_time()
        self.bot.log.info("Sending out a wave of ducks in %s seconds",
                          [wait])
        self.bot.add_timer("show-duck", wait, persist=False)

    def bootstrap(self, event):
        for server in self.bot.servers.values():
            for channel in server.channels.values():
                ducks_enabled = channel.get_setting("ducks-enabled", False)

                if ducks_enabled == True:
                    channel.set_setting("active-duck", False)

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

        for user, friends in sorted(friendliest.items(), key = itemgetter(1),
                                    reverse = True):
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

    def duck_bef(self, event):
        user = event["user"]
        target = user.nickname
        id = user.id

        active_duck = event["target"].get_setting("active-duck", False)

        if active_duck == False:
            if event["server"].has_user(target):
                if not event["server"].is_own_nickname(target):
                    event["target"].send_kick(target,
                                              "You tried befriending a non-existent duck. Creepy!")
                else:
                    event["stderr"].write("Nope.")
            else:
                event["stderr"].write("That user is not in this channel")
        else:
            befriended_ducks = event["target"].get_user_setting(id,
                                                                "ducks-befriended",
                                                                0)
            event["target"].set_user_setting(id,
                                             "ducks-befriended",
                                             befriended_ducks + 1)
            event["target"].set_setting("active-duck", False)

            grammar = "" if befriended_ducks == 0 else "s"

            event["stdout"].write(
                target + ", you've befriended " + Utils.bold(str(
                    befriended_ducks + 1)) + " duck" + grammar + " in " +
                Utils.bold(event[
                    "target"].name))

            self.duck_loop_entry(event)

    def duck_bang(self, event):
        user = event["user"]
        target = user.nickname
        id = user.id
        if not event["target"].get_setting("active-duck", False):
            event["stderr"].set_prefix("Kick")
            if event["server"].has_user(target):
                if not event["server"].is_own_nickname(target):
                    event["target"].send_kick(target,
                                              "You tried shooting a non-existent duck. Creepy!")
                else:
                    event["stderr"].write("Nope.")
            else:
                event["stderr"].write("That user is not in this channel")
        else:
            shot_ducks = event["target"].get_user_setting(id, "ducks-shot", 0)
            event["target"].set_user_setting(id, "ducks-shot", shot_ducks + 1)
            event["target"].set_setting("active-duck", False)

            grammar = "" if shot_ducks == 0 else "s"

            event["stdout"].write(
                target + ", you've shot "
                + Utils.bold(str(shot_ducks + 1)) + " duck"
                + grammar + " in "
                + Utils.bold(event["target"].name))

            self.duck_loop_entry(event)

    def get_random_duck_time(self):
        return random.randint(120, 1200)

    def show_duck(self, event):
        for server in self.bot.servers.values():
            for channel in server.channels.values():
                ducks_enabled = channel.get_setting("ducks-enabled", False)

                if ducks_enabled == False:
                    continue

                active_duck = channel.get_setting("active-duck", False)

                if ducks_enabled == True and active_duck == False:
                    channel.send_message(random.choice(DUCK_LIST))

                    channel.set_setting("active-duck", True)

                elif ducks_enabled == True and active_duck == True:
                    pass

                else:
                    channel.set_setting("active-duck", False)

    def duck_decoy(self, event):
        self.events.on("send").on("stdout").call(target=event["channel"],
            module_name="Ducks", server=event["server"],
            message=random.choice(DUCK_LIST))

    def set_decoy(self, event):
        next_decoy_time = self.get_random_duck_time()
        self.bot.add_timer("duck-decoy", next_decoy_time, persist=False,
            server=event["server"], channel=event["target"])
