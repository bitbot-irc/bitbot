import random
from src import ModuleManager, utils

DUCK = "・゜゜・。。・゜゜\_o< QUACK!"
NO_DUCK = "There was no duck!"

@utils.export("channelset", {"setting": "ducks-enabled",
    "help": "Whether or not to spawn ducks", "validate": utils.bool_or_none})
@utils.export("channelset", {"setting": "ducks-min-messages",
    "help": "Minimum messages between ducks spawning",
    "validate": utils.int_or_none})
@utils.export("channelset", {"setting": "ducks-kick",
    "help": "Whether or not to kick someone talking to non-existent ducks",
    "validate": utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    @utils.hook("new.channel")
    def new_channel(self, event):
        self.bootstrap_channel(event["channel"])

    def bootstrap_channel(self, channel):
        if not hasattr(channel, "duck_active"):
            channel.duck_active = False
            channel.duck_lines = 0

    def _activity(self, channel):
        self.bootstrap_channel(channel)

        ducks_enabled = channel.get_setting("ducks-enabled", False)

        if ducks_enabled and not channel.duck_active:
            channel.duck_lines += 1
            min_lines = channel.get_setting("ducks-min-messages", 20)

            if channel.duck_lines >= min_lines:
                show_duck = random.SystemRandom().randint(1, 10) == 1

                if show_duck:
                    self._trigger_duck(channel)

    @utils.hook("received.join")
    def join(self, event):
        self._activity(event["channel"])
    @utils.hook("received.message.channel")
    def channel_message(self, event):
        self._activity(event["channel"])

    def _trigger_duck(self, channel):
        channel.duck_active = True
        channel.send_message(DUCK)

    def _duck_action(self, channel, user, action, setting):
        channel.duck_active = False

        user_id = user.get_id()
        action_count = channel.get_user_setting(user_id, setting, 0)
        action_count += 1
        channel.set_user_setting(user_id, setting, action_count)

        return "%s %s a duck! You've %s %d ducks in %s!" % (
            user.nickname, action, action, action_count, channel.name)

    def _no_duck(self, channel, user, stderr, action):
        if channel.get_setting("ducks-kick"):
            channel.send_kick(user.nickname, NO_DUCK)
        else:
            stderr.write(NO_DUCK)

    @utils.hook("received.command.bef", alias_of="befriend")
    @utils.hook("received.command.befriend", channel_only=True)
    def befriend(self, event):
        if event["target"].duck_active:
            action = self._duck_action(event["target"], event["user"], "saved",
                "ducks-befriended")
            event["stdout"].write(action)
        else:
            self._no_duck(event["target"], event["user"], event["stderr"],
                "befriend")

    @utils.hook("received.command.bang", channel_only=True)
    def bang(self, event):
        if event["target"].duck_active:
            action = self._duck_action(event["target"], event["user"], "shot",
                "ducks-shot")
            event["stdout"].write(action)
        else:
            self._no_duck(event["target"], event["user"], event["stderr"],
                "shoot")

