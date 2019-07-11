#--depends-on commands

import random
from src import ModuleManager, utils

ACTIONS = [
    "cronch",
    "munch",
    "nom nom",
    "wriggles excitedly"
]

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.botsnack")
    @utils.kwarg("expect_output", False)
    def botsnack(self, event):
        event["target"].send_message("\x01ACTION %s\x01" %
            random.choice(ACTIONS))

