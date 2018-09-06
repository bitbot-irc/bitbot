import Utils

class Module(object):
    _name = "AutoMode"
    def __init__(self, bot, events, exports):
        self.bot = bot

        events.on("received.join").hook(self.on_join)

        events.on("received.command.addop").hook(self.add_op,
            require_mode="o", min_args=1, channel_only=True,
            usage="<nickname>", help="Add a user to the automode op list")
        events.on("received.command.removeop").hook(self.remove_op,
            require_mode="o", min_args=1, channel_only=True,
            usage="<nickname>", help="Remove a user from the automode "
            "op list")

        events.on("received.command.addvoice").hook(self.add_voice,
            require_mode="o", min_args=1, channel_only=True,
            usage="<nickname>", help="Add a user to the automode voice list")
        events.on("received.command.removevoice").hook(self.remove_voice,
            require_mode="o", min_args=1, channel_only=True,
            usage="<nickname>", help="Remove a user from the automode "
            "voice list")

        exports.add("channelset", {"setting": "automode",
            "help": "Disable/Enable automode",
            "validate": Utils.bool_or_none})

    def _check_modes(self, channel, user):
        identified_account = user.get_identified_account()
        if identified_account and channel.get_setting("automode", False):
            modes = channel.get_user_setting(user.get_id(), "automodes", [])
            if modes:
                channel.send_mode("+%s" % "".join(modes),
                    " ".join([user.nickname for mode in modes]))
    def on_join(self, event):
        self._check_modes(event["channel"], event["user"])
    def on_account(self, event):
        for channel in event["user"].channels:
            self._check_modes(channel, event["user"])

    def _add_mode(self, event, mode, mode_name):
        target_user = event["server"].get_user(event["args_split"][0])
        automodes = event["target"].get_user_setting(target_user.get_id(),
            "automodes", [])
        if mode in automodes:
            event["stderr"].write("'%s' already has automode %s" % (
                target_user.nickname, mode_name))
        else:
            automodes.append(mode)
            event["target"].set_user_setting(target_user.get_id(), "automodes",
                automodes)
            event["stdout"].write("Added automode %s for '%s'" % (
                mode_name, target_user.nickname))
    def _remove_mode(self, event, mode, mode_name):
        target_user = event["server"].get_user(event["args_split"][0])
        automodes = event["target"].get_user_setting(target_user.get_id(),
            "automodes", [])
        if not mode in automodes:
            event["stderr"].write("'%s' doesn't have automode %s" % (
                target_user.nickname, mode_name))
        else:
            automodes.remove(mode)
            event["target"].set_user_setting(target_user.get_id(), "automodes",
                automodes)
            event["stdout"].write("Removed automode %s from '%s'" % (
                mode_name, target_user.nickname))

    def add_op(self, event):
        self._add_mode(event, "o", "op")
    def remove_op(self, event):
        self._remove_mode(event, "o", "op")

    def add_voice(self, event):
        self._add_mode(event, "v", "voice")
    def remove_voice(self, event):
        self._remove_mode(event, "v", "voice")
