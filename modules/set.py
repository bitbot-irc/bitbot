

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        self.exports = exports

        events.on("received.command.set").hook(self.set,
            usage="<setting> <value>", help="Set a specified user setting")
        events.on("received.command.get").hook(self.get, min_args=1,
            usage="<setting>", help="Get a specified user setting")

        events.on("received.command.channelset").hook(self.channel_set,
            channel_only=True, usage="<setting> <value>", require_mode="o",
            help="Set a specified setting for the current channel")
        events.on("received.command.channelsetoverride").hook(
            self.channel_set, channel_only=True, usage="<setting> <value>",
            permission="channelsetoverride",
            help="Set a specified setting for the current channel")
        events.on("received.command.channelget").hook(self.channel_get,
            channel_only=True, usage="<setting>", min_args=1,
            require_mode="o", help="Get a specified setting for the current "
            "channel")

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
    def set(self, event):
        self._set(self.exports.get_all("set"), event, event["user"])

    def channel_set(self, event):
        self._set(self.exports.get_all("channelset"), event,
            event["target"])

    def _get(self, event, setting, qualifier, value):
        if not value == None:
            event["stdout"].write("'%s'%s: %s" % (setting,
                qualifier, str(value)))
        else:
            event["stdout"].write("'%s' has no value set" % setting)

    def channel_get(self, event):
        setting = event["args_split"][0]
        self._get(event, setting, " for %s" % event["target"].name,
            event["target"].get_setting(setting, None))

    def get(self, event):
        setting = event["args_split"][0]
        self._get(event, setting, "", event["user"].get_setting(
            setting, None))
