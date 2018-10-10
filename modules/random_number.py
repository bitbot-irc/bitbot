import random, uuid
from src import ModuleManager, utils

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

    @utils.hook("received.command.guid")
    def guid(self, event):
        """
        :help: Get a random guid
        """
        event["stdout"].write(str(uuid.uuid4()))
