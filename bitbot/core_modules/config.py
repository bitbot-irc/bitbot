#--depends-on channel_access
#--depends-on check_mode
#--depends-on commands
#--depends-on permissions

import enum
from bitbot import ModuleManager, utils

class ConfigInvalidValue(Exception):
    def __init__(self, message: str=None):
        self.message = message
class ConfigSettingInexistent(Exception):
    pass

class ConfigResults(enum.Enum):
    Changed = 1
    Retrieved = 2
    Removed = 3
    Unchanged = 4

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

        if context_desc == "*":
            if channel == user:
                # we're in PM
                return user, "set", None
            else:
                #we're in a channel
                return channel, "channelset", None
        elif server.is_channel(context_desc):
            return context_desc, "channelset", context_desc
        elif server.irc_lower(context_desc) == user.nickname_lower:
            return user, "set", None
        elif "user".startswith(context_desc_lower):
            return user, "set", None
        elif "channel".startswith(context_desc_lower):
            return channel, "channelset", None
        elif "server".startswith(context_desc_lower):
            return server, "serverset", None
        elif "bot".startswith(context_desc_lower):
            return self.bot, "botset", None
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
            target, setting_context, _ = self._to_context(event["server"],
                channel, event["user"], context)

            export_settings = self._get_export_setting(setting_context)
            setting_info = export_settings.get(require_setting, None)
            if setting_info:
                value = target.get_setting(require_setting, None)
                if value == None:
                    example = setting_info.example or "<value>"
                    if context == "user":
                        context = event["user"].nickname
                    elif context == "channel" and not channel == None:
                        context = channel.name
                    else:
                        context = context[0]

                    error = "Please set %s, e.g.: %sconfig %s %s %s" % (
                        require_setting, event["command_prefix"], context,
                        require_setting, example)
                    return utils.consts.PERMISSION_ERROR, error

    def _get_export_setting(self, context):
        settings = self.exports.get_all(context)
        return {setting.name.lower(): setting for setting in settings}

    def _config(self, export_settings, target, setting, value=None):
        if not value == None:
            setting_object = export_settings[setting]
            try:
                validated_value = setting_object.parse(value)
            except utils.settings.SettingParseException as e:
                raise ConfigInvalidValue(str(e))

            if not validated_value == None:
                existing_value = target.get_setting(setting, None)
                if existing_value == validated_value:
                    return ConfigResult(ConfigResults.Unchanged)
                else:
                    target.set_setting(setting, validated_value)
                    formatted_value = setting_object.format(validated_value)
                    return ConfigResult(ConfigResults.Changed, formatted_value)
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

    @utils.hook("received.command.c", alias_of="config")
    @utils.hook("received.command.config")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("help", "Change config options")
    @utils.kwarg("usage", "<context>[:name] [-][setting [value]]")
    def config(self, event):
        arg_count = len(event["args_split"])
        context_desc, _, name = event["args_split"][0].partition(":")

        setting = None
        value = None
        if arg_count > 1:
            setting = event["args_split"][1].lower()
            if arg_count > 2:
                value = " ".join(event["args_split"][2:])

        try:
            target, context, name_override = self._to_context(event["server"],
                event["target"], event["user"], context_desc)
        except ValueError:
            raise utils.EventError(
                "Unknown context '%s'. Please provide "
                "'user', 'channel', 'server' or 'bot'" % context_desc)

        name = name_override or name

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
            except ConfigInvalidValue as e:
                if not e.message == None:
                    raise utils.EventError("Invalid value: %s" % e.message)

                example = export_settings[setting].get_example()
                if not example == None:
                    raise utils.EventError("Invalid value. %s" %
                        example)
                else:
                    raise utils.EventError("Invalid value")
            except ConfigSettingInexistent:
                raise utils.EventError("Setting not set")

            for_str = ""
            if name_override:
                for_str = " for %s" % name_override
            if result.result == ConfigResults.Changed:
                event["stdout"].write("Config '%s'%s set to %s" %
                    (setting, for_str, result.data))
            elif result.result == ConfigResults.Retrieved:
                event["stdout"].write("%s%s: %s" % (setting, for_str,
                    result.data))
            elif result.result == ConfigResults.Removed:
                event["stdout"].write("Unset setting '%s'%s" %
                    (setting.lstrip("-"), for_str))
            elif result.result == ConfigResults.Unchanged:
                event["stdout"].write("Config '%s'%s unchanged" %
                    (setting, for_str))
        else:
            event["stdout"].write("Available config: %s" %
                ", ".join(export_settings.keys()))
