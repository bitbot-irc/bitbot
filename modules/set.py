from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _set(self, settings, event, target):
        settings_dict = dict([(setting["setting"], setting
            ) for setting in settings])
        if len(event["args_split"]) > 1:
            setting = event["args_split"][0].lower()
            if setting in settings_dict:
                value = " ".join(event["args_split"][1:])
                value = settings_dict[setting].get("validate",
                    lambda x: x)(value)
                if not value == None:
                    target.set_setting(setting, value)
                    event["stdout"].write("Saved setting")
                else:
                    event["stderr"].write("Invalid value")
            else:
                event["stderr"].write("Unknown setting")
        elif len(event["args_split"]) == 1:
            event["stderr"].write("Please provide a value")
        else:
            event["stdout"].write("Available settings: %s" % (
                ", ".join(settings_dict.keys())))
    @utils.hook("received.command.set")
    def set(self, event):
        """
        :help: Set a specified user setting
        :usage: <setting> <value>
        """
        self._set(self.exports.get_all("set"), event, event["user"])

    @utils.hook("received.command.channelset", channel_only=True,
        require_mode="o")
    @utils.hook("received.command.channelsetoverride", channel_only=True,
        permission="channelsetoverride")
    def channel_set(self, event):
        """
        :help: Get a specified channel setting for the current channel
        :usage: <setting> <value>
        """
        self._set(self.exports.get_all("channelset"), event, event["target"])

    @utils.hook("received.command.serverset")
    def server_set(self, event):
        """
        :help: Set a specified server setting for the current server
        :usage: <setting> <value>
        :permission: serverset
        """
        self._set(self.exports.get_all("serverset"), event, event["server"])

    @utils.hook("received.command.botset")
    def bot_set(self, event):
        """
        :help: Set a specified bot setting
        :usage: <setting> <value>
        :permission: botset
        """
        self._set(self.exports.get_all("botset"), event, self.bot)

    def _get(self, event, setting, qualifier, value):
        if not value == None:
            event["stdout"].write("'%s'%s: %s" % (setting,
                qualifier, str(value)))
        else:
            event["stdout"].write("'%s' has no value set" % setting)

    @utils.hook("received.command.get", min_args=1)
    def get(self, event):
        """
        :help: Get a specified user setting
        :usage: <setting>
        """
        setting = event["args_split"][0]
        self._get(event, setting, "", event["user"].get_setting(
            setting, None))

    @utils.hook("received.command.channelget", channel_only=True, min_args=1)
    def channel_get(self, event):
        """
        :help: Get a specified channel setting for the current channel
        :usage: <setting>
        :require_mode: o
        """
        setting = event["args_split"][0]
        self._get(event, setting, " for %s" % event["target"].name,
            event["target"].get_setting(setting, None))

    @utils.hook("received.command.serverget", min_args=1)
    def server_get(self, event):
        """
        :help: Get a specified server setting for the current server
        :usage: <setting>
        :permission: serverget
        """
        setting = event["args_split"][0]
        self._get(event, setting, "", event["server"].get_setting(
            setting, None))

    @utils.hook("received.command.botget", min_args=1)
    def bot_get(self, event):
        """
        :help: Get a specified bot setting
        :usage: <setting>
        :permission: botget
        """
        setting = event["args_split"][0]
        self._get(event, setting, "", self.bot.get_setting(setting, None))
