from src import ModuleManager, Utils

@Utils.export("channelset", {"setting": "automode",
    "help": "Disable/Enable automode", "validate": Utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    _name = "AutoMode"

    def _check_modes(self, channel, user):
        identified_account = user.get_identified_account()
        if identified_account and channel.get_setting("automode", False):
            modes = channel.get_user_setting(user.get_id(), "automodes", [])
            if modes:
                channel.send_mode("+%s" % "".join(modes),
                    " ".join([user.nickname for mode in modes]))

    @Utils.hook("received.join")
    def on_join(self, event):
        self._check_modes(event["channel"], event["user"])
    @Utils.hook("received.account")
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
            if event["target"] in target_user.channels:
                self._check_modes(event["target"], target_user)

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

    @Utils.hook("received.command.addop", require_mode="o", min_args=1,
        channel_only=True, usage="<nickname>")
    def add_op(self, event):
        """
        Add a user to the auto-mode list as an op
        """
        self._add_mode(event, "o", "op")
    @Utils.hook("received.command.removeop", require_mode="o", min_args=1,
        channel_only=True, usage="<nickname>")
    def remove_op(self, event):
        """
        Remove a user from the auto-mode list as an op
        """
        self._remove_mode(event, "o", "op")

    @Utils.hook("received.command.addvoice", require_mode="o", min_args=1,
        channel_only=True, usage="<nickname>")
    def add_voice(self, event):
        """
        Add a user to the auto-mode list as a voice
        """
        self._add_mode(event, "v", "voice")
    @Utils.hook("received.command.removevoice", require_mode="o", min_args=1,
        channel_only=True, usage="<nickname>")
    def remove_voice(self, event):
        """
        Remove a user from the auto-mode list as anvoice
        """
        self._remove_mode(event, "v", "voice")
