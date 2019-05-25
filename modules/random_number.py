#--depends-on commands

import random, uuid
from src import ModuleManager, utils

COIN_SIDES = ["heads", "tails"]

class Module(ModuleManager.BaseModule):
    _name = "Random"

    @utils.hook("received.command.rand", alias_of="random")
    @utils.hook("received.command.random")
    def random(self, event):
        """
        :help: Get a random number
        :usage: [start] [end]
        """
        start, end = "1", "100"
        if len(event["args_split"]) > 1:
            start, end = event["args_split"][:2]
        elif len(event["args_split"]) == 1:
            end = event["args_split"][0]
        if start.isdigit() and end.isdigit():
            start, end = int(start), int(end)
            if end > start:
                number = random.randint(start, end)
                event["stdout"].write("(%d-%d) %d" % (start, end,
                    number))
            else:
                event["stderr"].write(
                    "End must be greater than start")
        else:
            event["stderr"].write(
                "Both start and end must be valid integers")

    @utils.hook("received.command.cointoss")
    def coin_toss(self, event):
        chosen_side = random.SystemRandom().choice(COIN_SIDES)
        event["stdout"].write("%s tosses a coin and gets %s" %
            (event["user"].nickname, chosen_side))

    @utils.hook("received.command.uuid4")
    def uuid(self, event):
        """
        :help: Get a random uuid4
        """
        event["stdout"].write(str(uuid.uuid4()))
