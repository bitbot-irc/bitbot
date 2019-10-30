#--depends-on commands

import difflib
from src import ModuleManager, utils

SETTING = utils.BoolSetting("command-suggestions",
    "Disable/enable command suggestions")
@utils.export("serverset", SETTING)
@utils.export("channelset", SETTING)
class Module(ModuleManager.BaseModule):
    def _all_command_hooks(self):
        return self.events.on("received.command").get_children()

    @utils.hook("unknown.command")
    def unknown_command(self, event):
        if not event["server"].get_setting("command-suggestions",
                event["target"].get_setting("command-suggestions", True)):
            return

        all_commands = self._all_command_hooks()
        match = difflib.get_close_matches(event["command"], all_commands,
            cutoff=0.7)
        if match:
            nickname = ""
            if event["is_channel"]:
                nickname = "%s: " % event["user"].nickname

            event["target"].send_message(
                "%sUnknown command. Did you mean %s%s?" % (
                nickname, event["command_prefix"], match[0]))
