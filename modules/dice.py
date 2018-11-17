import random
from src import ModuleManager, utils

ERROR_FORMAT = "Incorrect format! Format must be [number]d[number], e.g. 1d20"

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.roll", min_args=1)
    def roll_dice(self, event):
        """
        :help: Roll some dice, DND style!
        :usage: [1-5]d[1-20]
        """
        roll = event["args_split"][0].lower()
        count, _, sides = roll.partition("d")
        if not count.isdigit() or not sides.isdigit():
            raise utils.EventError(ERROR_FORMAT)

        count_n = min(5, int(count))
        sides_n = min(20, int(sides))

        results = random.choices(range(1, sides_n), k=count_n)

        total_n = sum(results)
        total = ""
        if len(results) > 1:
            total = " (total: %d)" % total_n

        event["stdout"].write("Rolled %s and got %s%s" % (
            roll, total_n, ", ".join(str(r) for r in results)))
