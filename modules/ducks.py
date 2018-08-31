import datetime
import random

import IRCLogging

DUCK_LAST_SEEN = datetime.datetime.now()


class Module(object):
    def __init__(self, bot):
        self.log = IRCLogging.Log
        self.bot = bot
        self.active_duck = 0

        bot.events.on("received.command.bef").hook(self.duck_bef,
                                                   help="Befriend a duck!")
        bot.events.on("received.command.bang").hook(self.duck_bang,
                                                    help="Shoot a duck! Meanie.")
        # bot.events.on("received.command.friends").hook(self.duck_friends,
        #                                             help="See who the friendliest people to ducks are!")
        # bot.events.on("received.command.killers").hook(self.duck_killers,
        #                                             help="See who shoots the most amount of ducks.")
        # bot.events.on("received.command.ducks").hook(self.duck_list,
        #                                              help="Shows a list of the most popular duck superstars.")

        now = datetime.datetime.now()
        next_duck_time = random.randint(30, 40)

        self.duck_times = {}

        tricky = next_duck_time - now.second
        tricky += ((next_duck_time - (now.minute + 1)) * 2)

        bot.events.on("postboot").on("configure").on(
            "channelset").assure_call(setting="ducks-enabled",
                                      help="Toggles ducks! (1 or 0)")

        bot.events.on("postboot").on("configure").on(
            "channelset").assure_call(setting="min-duck-time",
                                      help="Minimum seconds before a duck is summoned")

        bot.events.on("postboot").on("configure").on(
            "channelset").assure_call(setting="max-duck-time",
                                      help="Max seconds before a duck is summoned")

        bot.events.on("timer").on("duck-appear").hook(self.show_duck)
        bot.add_timer("duck-appear", next_duck_time, persist=False)

        bot.events.on("received.numeric.366").hook(self.bootstrap)

    def bootstrap(self, event):
        for server in self.bot.servers.values():
            for channel in server.channels.values():
                ducks_enabled = channel.get_setting("ducks-enabled", 0)
                ducks_enabled = int(ducks_enabled) if isinstance(ducks_enabled, str) else ducks_enabled

                min_time = "min-duck-time-%s" % channel.name
                max_time = "max-duck-time-%s" % channel.name

                min_duck_time = channel.get_setting("min-duck-time", 240)
                max_duck_time = channel.get_setting("max-duck-time", 1200)

                min_duck_time = int(min_duck_time) if isinstance(min_duck_time, str) else min_duck_time
                max_duck_time = int(max_duck_time) if isinstance(max_duck_time, str) else max_duck_time

                self.duck_times[min_time] = min_duck_time
                self.duck_times[max_time] = max_duck_time

                if ducks_enabled == 1:
                    channel.set_setting("active-duck", 0)

        print(self.duck_times)

    def duck_time(self, channel):
        if isinstance(channel, str):
            channel_name = channel
        else:
            channel_name = channel["target"].name

        min = "min-duck-time-%s" % (channel_name)
        max = "max-duck-time-%s" % (channel_name)

        self.bot.log.debug("Attempting to set %s to %s", [str(min), str(self.duck_times[min])]);
        self.bot.log.debug("Attempting to set %s to %s", [str(max), str(self.duck_times[max])]);

        return random.randint(self.duck_times[min], self.duck_times[max])

    def duck_bef(self, event):
        target = event["user"].nickname
        active_duck = event["target"].get_setting("active-duck", 0)
        active_duck = int(active_duck) if isinstance(active_duck, str) else active_duck

        if active_duck == 0:
            event["stderr"].set_prefix("Kick")
            if event["server"].has_user(target):
                if not event["server"].is_own_nickname(target):
                    event["target"].send_kick(target, "You tried befriending a non-existent duck. Creepy!")
                else:
                    event["stderr"].write("Nope.")
            else:
                event["stderr"].write("That user is not in this channel")
        else:
            setting = "bef-ducks-%s-%s" % (target, event["target"].name)
            befriended_ducks = event["server"].get_setting(setting, 0)
            event["server"].set_setting(setting, befriended_ducks + 1)
            event["target"].set_setting("active-duck", 0)

            grammar = "" if befriended_ducks == 0 else "s"

            event["stdout"].write(
                target + ", you've befriended " + str(befriended_ducks + 1) + " duck" + grammar + " in " + event[
                    "target"].name);

            next_duck_time = self.duck_time(event)
            self.bot.add_timer("duck-appear", next_duck_time, persist=False)

    def duck_bang(self, event):
        target = event["user"].nickname
        if event["target"].get_setting("active-duck", 0) == 0:
            event["stderr"].set_prefix("Kick")
            if event["server"].has_user(target):
                if not event["server"].is_own_nickname(target):
                    event["target"].send_kick(target, "You tried shooting a non-existent duck. Creepy!")
                else:
                    event["stderr"].write("Nope.")
            else:
                event["stderr"].write("That user is not in this channel")
        else:
            setting = "shot-ducks-%s-%s" % (target, event["target"].name)
            shot_ducks = event["server"].get_setting(setting, 0)
            event["server"].set_setting(setting, shot_ducks + 1)
            event["target"].set_setting("active-duck", 0)

            grammar = "" if shot_ducks == 0 else "s"

            event["stdout"].write(
                target + ", you've shot " + str(shot_ducks + 1) + " duck" + grammar + " in " + event["target"].name);

            next_duck_time = self.duck_time(event)
            self.bot.add_timer("duck-appear", next_duck_time, persist=False)

    def show_duck(self, event):
        for server in self.bot.servers.values():
            for channel in server.channels.values():
                ducks_enabled = channel.get_setting("ducks-enabled", 0)
                ducks_enabled = int(ducks_enabled) if isinstance(ducks_enabled, str) else ducks_enabled
                if ducks_enabled == 0:
                    continue

                self.bot.log.info("Ducks enabled for %s: %s", [str(channel.name), str(ducks_enabled)])
                active_duck = channel.get_setting("active-duck", 0)
                active_duck = int(active_duck) if isinstance(active_duck, str) else active_duck

                if ducks_enabled == 1 and active_duck == 0:
                    ducks = [
                        "・゜゜・。。・゜ ​ ゜\_O​< q​uack!",
                        "・゜゜・。。・゜ ​ ゜\_o< QUACK!",
                        "・゜゜・。 ​ 。・゜゜\​_ó< qu​ack!",
                        "・゜゜・。 ​ 。・゜゜\​_ó< qu​ack quack!",
                        "・゜゜ 。 ​ 。・゜  \​_ó< bawk!",
                        "・゜゜ 。 ​ 。・゜゜\​_ó< squawk!",
                        "・ ゜・。 ​ 。・゜゜ \​_ó< beep beep!"
                    ]

                    channel.send_message(random.choice(ducks))

                    channel.set_setting("active-duck", 1)

                elif ducks_enabled == 1 and active_duck == 1:
                    pass

                else:
                    channel.set_setting("active-duck", 0)

                    next_duck_time = self.duck_time(channel.name)
                    self.bot.add_timer("duck-appear", next_duck_time, persist=False)

    # def coins(self, event):
    #    if event["args_split"]:
    #        target = event["server"].get_user(event["args_split"][0])
    #    else:
    #        target = event["user"]
    #    coins = decimal.Decimal(target.get_setting("coins", "0.0"))
    #    event["stdout"].write("%s has %s coin%s" % (target.nickname,
    #        "{0:.2f}".format(coins), "" if coins == 1 else "s"))
