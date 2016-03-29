import random

class Module(object):
    def __init__(self, bot):
        bot.events.on("received").on("command").on("random",
            "rand").hook(self.random)

    def random(self, event):
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
