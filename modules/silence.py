import time
from src import ModuleManager, utils

SILENCE_TIME = 60*5 # 5 minutes

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.silence", channel_only=True)
    def silence(self, event):
        """
        :help: Silence me for 5 minutes
        :require_mode: high
        """
        silence_until = time.time()+SILENCE_TIME
        event["target"].set_setting("silence-until", silence_until)
        event["stdout"].write("Ok, I'll be back")

    @utils.hook("preprocess.command")
    def preprocess_command(self, event):
        if event["is_channel"]:
            silence_until = event["target"].get_setting("silence-until", None)
            if silence_until:
                if time.time()<silence_until:
                    return utils.consts.PERMISSION_HARD_FAIL
                else:
                    event["target"].del_setting("silence-until")
