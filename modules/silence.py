#--depends-on commands
#--depends-on permissions

import time
from src import EventManager, ModuleManager, utils

SILENCE_TIME = 60*5 # 5 minutes

class Module(ModuleManager.BaseModule):
    def on_load(self):
        self.exports.add("is-silenced", self._is_silenced)

    def _is_silenced(self, target):
        silence_until = target.get_setting("silence-until", None)
        if silence_until and time.time()<silence_until:
            return True
        return False

    @utils.hook("received.command.silence", channel_only=True)
    def silence(self, event):
        """
        :help: Silence me for 5 minutes
        :require_mode: high
        :permission: silence
        """
        silence_until = time.time()+SILENCE_TIME
        event["target"].set_setting("silence-until", silence_until)
        event["stdout"].write("Ok, I'll be back")

    @utils.hook("preprocess.command", priority=EventManager.PRIORITY_HIGH)
    def preprocess_command(self, event):
        if event["is_channel"]:
            silence_until = event["target"].get_setting("silence-until", None)
            if silence_until:
                if self._is_silenced(event["target"]):
                    return utils.consts.PERMISSION_HARD_FAIL
                else:
                    event["target"].del_setting("silence-until")
