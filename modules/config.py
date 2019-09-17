#--depends-on channel_access
#--depends-on check_mode
#--depends-on commands
#--depends-on permissions

import enum
from src import ModuleManager, utils

class ConfigInvalidValue(Exception):
    pass
class ConfigSettingInexistent(Exception):
    pass

class ConfigResults(enum.Enum):
    Changed = 1
    Retrieved = 2
    Removed = 3
class ConfigResult(object):
    def __init__(self, result, data=None):
        self.result = result
        self.data = data

class ConfigChannelTarget(object):
    def __init__(self, bot, server, channel_name):
        self._bot = bot
        self._server = server
        self._channel_name = channel_name
    def _get_id(self):
        return self._server.channels.get_id(self._channel_name)
    def set_setting(self, setting, value):
        channel_id = self._get_id()
        self._bot.database.channel_settings.set(channel_id, setting, value)
    def get_setting(self, setting, default=None):
        channel_id = self._get_id()
        return self._bot.database.channel_settings.get(channel_id, setting,
            default)
    def del_setting(self, setting):
        channel_id = self._get_id()
        self._bot.database.channel_settings.delete(channel_id, setting)

    def get_user_setting(self, user_id, setting, default=None):
        return self._bot.database.user_channel_settings.get(user_id,
            self._get_id(), setting, default)

class Module(ModuleManager.BaseModule):
    def _to_context(self, server, channel, user, context_desc):
        context_desc_lower = context_desc.lower()

        if context_desc_lower[0] in server.channel_types:
            return context_desc, "channelset"
        elif server.irc_lower(context_desc) == user.nickname_lower:
            return user, "set"
        elif "user".startswith(context_desc_lower):
            return user, "set"
        elif "channel".startswith(context_desc_lower):
            return channel, "channelset"
        elif "server".startswith(context_desc_lower):
            return server, "serverset"
        elif "bot".startswith(context_desc_lower):
            return self.bot, "botset"
        else:
            raise ValueError()

    @utils.hook("preprocess.command")
    def preprocess_command(self, event):
        require_setting = event["hook"].get_kwarg("require_setting", None)
        if not require_setting == None:
            require_setting_unless = event["hook"].get_kwarg(
                "require_setting_unless", None)
            if not require_setting_unless == None:
                require_setting_unless = int(require_setting_unless)
                if len(event["args_split"]) >= require_setting_unless:
                    return

            context, _, require_setting = require_setting.rpartition(":")
            require_setting = require_setting.lower()
            channel = None
            if event["is_channel"]:
                channel = event["target"]

            context = context or "user"
            target, setting_context = self._to_context(event["server"], channel,
                event["user"], context)

            export_settings = self._get_export_setting(setting_context)
            setting_info = export_settings.get(require_setting, None)
            if setting_info:
                value = target.get_setting(require_setting, None)
                if value == None:
                    example = setting_info.example or "<value>"
                    return "Please set %s, e.g.: %sconfig %s %s %s" % (
                        require_setting, event["command_prefix"], context[0],
                        require_setting, example)

    def _get_export_setting(self, context):
        settings = self.exports.get_all(context)
        return {setting.name.lower(): setting for setting in settings}

    def _config(self, export_settings, target, setting, value=None):
        if not value == None:
            validated_value = export_settings[setting].parse(value)
            if not validated_value == None:
                target.set_setting(setting, validated_value)
                return ConfigResult(ConfigResults.Changed, validated_value)
            else:
                raise ConfigInvalidValue()
        else:
            unset = False
            if setting.startswith("-"):
                setting = setting[1:]
                unset = True

            existing_value = target.get_setting(setting, None)
            if not existing_value == None:
                if unset:
                    target.del_setting(setting)
                    return ConfigResult(ConfigResults.Removed)
                else:
                    formatted = export_settings[setting].format(existing_value)
                    return ConfigResult(ConfigResults.Retrieved, formatted)
            else:
                raise ConfigSettingInexistent()

    @utils.hook("received.command.config", min_args=1)
    def config(self, event):
        """
        :help: Change config options
        :usage: <context>[:name] [-][setting [value]]
        """

        arg_count = len(event["args_split"])
        context_desc, _, name = event["args_split"][0].partition(":")

        setting = None
        value = None
        if arg_count > 1:
            setting = event["args_split"][1].lower()
            if arg_count > 2:
                value = " ".join(event["args_split"][2:])

        try:
            target, context = self._to_context(event["server"],
                event["target"], event["user"], context_desc)
        except ValueError:
            raise utils.EventError(
                "Unknown context '%s'. Please provide "
                "'user', 'channel', 'server' or 'bot'" % context_desc)

        permission_check = utils.Check("permission", "config")

        if context == "set":
            if name:
                event["check_assert"](
                    utils.Check("self", name)|permission_check)
                target = event["server"].get_user(name)
            else:
                target = event["user"]
        elif context == "channelset":
            if name:
                if name in event["server"].channels:
                    target = event["server"].channels.get(name)
                else:
                    target = ConfigChannelTarget(self.bot, event["server"],
                        name)
            else:
                if event["is_channel"]:
                    target = event["target"]
                else:
                    raise utils.EventError(
                        "Cannot change config for current channel when in "
                        "private message")
            event["check_assert"](permission_check|
                utils.Check("channel-access", target, "config")|
                utils.Check("channel-mode", target, "o"))
        elif context == "serverset" or context == "botset":
            event["check_assert"](permission_check)

        export_settings = self._get_export_setting(context)
        if not setting == None:
            if not setting.lstrip("-") in export_settings:
                raise utils.EventError("Setting not found")

            try:
                result = self._config(export_settings, target, setting, value)
            except ConfigInvalidValue:
                example = export_settings[setting].get_example()
                if not example == None:
                    raise utils.EventError("Invalid value. %s" %
                        example)
                else:
                    raise utils.EventError("Invalid value")
            except ConfigSettingInexistent:
                raise utils.EventError("Setting not set")

            if result.result == ConfigResults.Changed:
                event["stdout"].write("Config '%s' set to %s" %
                    (setting, result.data))
            elif result.result == ConfigResults.Retrieved:
                event["stdout"].write("%s: %s" % (setting, result.data))
            elif result.result == ConfigResults.Removed:
                event["stdout"].write("Unset setting")
        else:
            event["stdout"].write("Available config: %s" %
                ", ".join(export_settings.keys()))
