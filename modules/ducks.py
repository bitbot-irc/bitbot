#--depends-on commands
#--depends-on config

import random, time
from src import EventManager, ModuleManager, utils

DUCK = "・゜゜・。。・゜゜\_o< QUACK!"
NO_DUCK = "There was no duck!"

DEFAULT_MIN_MESSAGES = 100

@utils.export("channelset", {"setting": "ducks-enabled",
    "help": "Whether or not to spawn ducks", "validate": utils.bool_or_none,
    "example": "on"})
@utils.export("channelset", {"setting": "ducks-min-messages",
    "help": "Minimum messages between ducks spawning",
    "validate": utils.int_or_none, "example": "50"})
@utils.export("channelset", {"setting": "ducks-kick",
    "help": "Whether or not to kick someone talking to non-existent ducks",
    "validate": utils.bool_or_none, "example": "on"})
class Module(ModuleManager.BaseModule):
    @utils.hook("new.channel")
    def new_channel(self, event):
        self.bootstrap_channel(event["channel"])

    def bootstrap_channel(self, channel):
        if not hasattr(channel, "duck_active"):
            channel.duck_active = None
            channel.duck_lines = 0

    def _activity(self, channel):
        self.bootstrap_channel(channel)

        ducks_enabled = channel.get_setting("ducks-enabled", False)

        if ducks_enabled and not channel.duck_active:
            channel.duck_lines += 1
            min_lines = channel.get_setting("ducks-min-messages",
                DEFAULT_MIN_MESSAGES)

            if channel.duck_lines >= min_lines:
                show_duck = random.SystemRandom().randint(1, 20) == 1

                if show_duck:
                    self._trigger_duck(channel)

    @utils.hook("command.regex", expect_output=False)
    def channel_message(self, event):
        """
        :pattern: .+
        :command: duck-trigger
        """
        self._activity(event["target"])

    def _trigger_duck(self, channel):
        channel.duck_lines = 0
        channel.duck_active = time.time()
        channel.send_message(DUCK)

    def _duck_action(self, channel, user, action, setting):
        duck_timestamp = channel.duck_active
        channel.duck_active = None

        user_id = user.get_id()
        action_count = channel.get_user_setting(user_id, setting, 0)
        action_count += 1
        channel.set_user_setting(user_id, setting, action_count)

        seconds = round(time.time()-duck_timestamp, 2)

        return "%s %s a duck in %s seconds! You've %s %d ducks in %s!" % (
            user.nickname, action, seconds, action, action_count, channel.name)

    def _no_duck(self, channel, user, stderr):
        if channel.get_setting("ducks-kick"):
            channel.send_kick(user.nickname, NO_DUCK)
        else:
            stderr.write(NO_DUCK)

    @utils.hook("received.command.bef", alias_of="befriend")
    @utils.hook("received.command.befriend", channel_only=True)
    def befriend(self, event):
        """
        :help: Befriend a duck
        """
        if event["target"].duck_active:
            action = self._duck_action(event["target"], event["user"], "saved",
                "ducks-befriended")
            event["stdout"].write(action)
        else:
            self._no_duck(event["target"], event["user"], event["stderr"])

    @utils.hook("received.command.trap", channel_only=True)
    def trap(self, event):
        """
        :help: Trap a duck
        """
        if event["target"].duck_active:
            action = self._duck_action(event["target"], event["user"], "trapped",
                "ducks-shot")
            event["stdout"].write(action)
        else:
            self._no_duck(event["target"], event["user"], event["stderr"])

    @utils.hook("received.command.friends")
    def friends(self, event):
        """
        :help: Show top 10 duck friends
        :usage: [channel]
        """
        stats = self._duck_stats(event["server"], "ducks-befriended", "friends",
            event["args_split"][0] if event["args"] else None)
        event["stdout"].write(stats)
    @utils.hook("received.command.enemies")
    def enemies(self, event):
        """
        :help: Show top 10 duck enemies
        :usage: [channel]
        """
        stats = self._duck_stats(event["server"], "ducks-shot", "enemies",
            event["args_split"][0] if event["args"] else None)
        event["stdout"].write(stats)

    def _duck_stats(self, server, setting, description, channel_query):
        channel_query_str = ""
        if not channel_query == None:
            channel_query = server.irc_lower(channel_query)
            channel_query_str = " in %s" % channel_query

        stats = server.find_all_user_channel_settings(setting)

        user_stats = {}
        for channel, nickname, value in stats:
            if not channel_query or channel_query == channel:
                if not nickname in user_stats:
                    user_stats[nickname] = 0
                user_stats[nickname] += value

        top_10 = utils.top_10(user_stats,
            convert_key=lambda nickname: server.get_user(nickname).nickname)
        return "Top duck %s%s: %s" % (description, channel_query_str,
            ", ".join(top_10))

