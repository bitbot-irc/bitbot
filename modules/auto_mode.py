from src import ModuleManager, utils

@utils.export("channelset", {"setting": "automode",
    "help": "Disable/Enable automode", "validate": utils.bool_or_none,
    "example": "on"})
class Module(ModuleManager.BaseModule):
    _name = "AutoMode"

    def _get_modes(self, channel, user):
        identified_account = user.get_identified_account()
        if identified_account and channel.get_setting("automode", False):
            modes = channel.get_user_setting(user.get_id(), "automodes", [])
            return modes
        return []
    def _check_modes(self, channel, user):
        modes = self._get_modes(channel, user)
        if modes:
            current_modes = channel.get_user_status(user)
            new_modes = set(modes)-current_modes
            channel.send_mode("+%s" % "".join(new_modes),
                [user.nickname for mode in new_modes])

    @utils.hook("received.join")
    def on_join(self, event):
        self._check_modes(event["channel"], event["user"])
    @utils.hook("received.account.login")
    @utils.hook("internal.identified")
    def on_account(self, event):
        for channel in event["user"].channels:
            self._check_modes(channel, event["user"])

    def _check_channel(self, channel):
        modes = []
        for user in channel.users:
            user_modes = self._get_modes(channel, user)
            for user_mode in user_modes:
                if not channel.has_mode(user, user_mode):
                    modes.append([user_mode, user.nickname])

        # break up in to chunks of (maximum) 3
        # https://tools.ietf.org/html/rfc2812.html#section-3.2.3
        mode_chunks = [modes[i:i+3] for i in range(0, len(modes), 3)]
        for chunk in mode_chunks:
            modes = [item[0] for item in chunk]
            nicknames = [item[1] for item in chunk]
            channel.send_mode(
                "+%s" % "".join(modes), nicknames)
    @utils.hook("received.command.syncmodes", channel_only=True)
    def sync_modes(self, event):
        """
        :help: Check/sync user modes
        :require_mode: o
        :require_access: syncmodes
        """
        self._check_channel(event["target"])

    @utils.hook("set.channelset.automode")
    def on_automode_set(self, event):
        if event["value"]:
            self._check_channel(event["target"])

    @utils.hook("self.join")
    def self_join(self, event):
        self._check_channel(event["channel"])

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
            if automodes:
                event["target"].set_user_setting(target_user.get_id(),
                    "automodes", automodes)
            else:
                event["target"].del_user_setting(target_user.get_id(),
                    "automodes")
            event["stdout"].write("Removed automode %s from '%s'" % (
                mode_name, target_user.nickname))

    @utils.hook("received.command.addop", min_args=1, channel_only=True)
    def add_op(self, event):
        """
        :help: Add a user to the auto-mode list as an op
        :usage: <nickname>
        :require_mode: o
        :require_access: autoop
        """
        self._add_mode(event, "o", "op")
    @utils.hook("received.command.removeop", min_args=1, channel_only=True)
    def remove_op(self, event):
        """
        :help: Remove a user from the auto-mode list as an op
        :usage: <nickname>
        :require_mode: o
        :require_access: autoop
        """
        self._remove_mode(event, "o", "op")

    @utils.hook("received.command.addvoice", min_args=1, channel_only=True)
    def add_voice(self, event):
        """
        :help: Add a user to the auto-mode list as a voice
        :usage: <nickname>
        :require_mode: o
        :require_access: autovoice
        """
        self._add_mode(event, "v", "voice")
    @utils.hook("received.command.removevoice", min_args=1, channel_only=True)
    def remove_voice(self, event):
        """
        :help: Remove a user from the auto-mode list as a voice
        :usage: <nickname>
        :require_mode: o
        :require_access: autovoice
        """
        self._remove_mode(event, "v", "voice")
