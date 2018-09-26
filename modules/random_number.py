import random, uuid
from src import ModuleManager, Utils

class Module(ModuleManager.BaseModule):
    _name = "Random"

    @Utils.hook("received.command.random|rand", usage="[start] [end]")
    def random(self, event):
        """
        Get a random number
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

    @Utils.hook("received.command.guid")
    def guid(self, event):
        """
        Get a random guid
        """
        event["stdout"].write(str(uuid.uuid4()))
