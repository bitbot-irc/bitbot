import random
from src import EventManager, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("get.command")
    @utils.kwarg("priority", EventManager.PRIORITY_HIGH)
    def get_command(self, event):
        event["kwargs"]["NICK"] = event["user"].nickname
        if event["is_channel"]:
            event["kwargs"]["CHAN"] = event["target"].name
            random_user = random.choice(list(event["target"].users))
            event["kwargs"]["RNICK"] = random_user.nickname
