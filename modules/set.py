from src import Utils

class Module(object):
    def __init__(self, bot, events, exports):
        self.exports = exports

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
    @Utils.hook("received.command.set", usage="<setting> <value>")
    def set(self, event):
        """
        Set a specified user setting
        """
        self._set(self.exports.get_all("set"), event, event["user"])

    @Utils.hook("received.command.channelset", channel_only=True,
        usage="<setting> <value>", require_mode="o")
    @Utils.hook("received.command.channelsetoverride", channel_only=True,
        usage="<setting> <value>", permission="channelsetoverride")
    def channel_set(self, event):
        """
        Get a specified channel setting for the current channel
        """
        self._set(self.exports.get_all("channelset"), event, event["target"])

    @Utils.hook("received.command.serverset", usage="<setting> <value>",
        permission="serverset")
    def server_set(self, event):
        """
        Set a specified server setting for the current server
        """
        self._set(self.exports.get_all("serverset"), event, event["server"])

    def _get(self, event, setting, qualifier, value):
        if not value == None:
            event["stdout"].write("'%s'%s: %s" % (setting,
                qualifier, str(value)))
        else:
            event["stdout"].write("'%s' has no value set" % setting)

    @Utils.hook("received.command.get", min_args=1, usage="<setting>")
    def get(self, event):
        """
        Get a specified user setting
        """
        setting = event["args_split"][0]
        self._get(event, setting, "", event["user"].get_setting(
            setting, None))

    @Utils.hook("received.command.channelget", channel_only=True,
        usage="<setting>", min_args=1, require_mode="o")
    def channel_get(self, event):
        """
        Get a specified channel setting for the current channel
        """
        setting = event["args_split"][0]
        self._get(event, setting, " for %s" % event["target"].name,
            event["target"].get_setting(setting, None))

    @Utils.hook("received.command.serverget", usage="<setting>", min_args=1,
        permission="serverget")
    def server_get(self, event):
        """
        Get a specified server setting for the current server
        """
        setting = event["args_split"][0]
        self._get(event, setting, "", event["server"].get_setting(
            setting, None))
