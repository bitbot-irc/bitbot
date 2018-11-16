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
        raw_input = event["args_split"][0]
        roll = raw_input.split("d")
        results = []

        if len(roll) is not 2:
            raise utils.EventError(ERROR_FORMAT)

        if roll[0].isdigit() is False or roll[1].isdigit() is False:
            raise utils.EventError(ERROR_FORMAT)

        roll = [int(roll[0]), int(roll[1])]

        num_of_die = 5 if roll[0] > 5 else roll[0]
        sides_of_die = 20 if roll[1] > 20 else roll[1]

        str_roll = str(num_of_die) + "d" + str(sides_of_die)

        for i in range(0, num_of_die):
            results.append(random.randint(1, sides_of_die))

        total_n = sum(results)
        total = ""
        if len(results) > 1:
            total = " (total: %d)" % total_n
        event["stdout"].write("Rolled %s and got %s%s" % (
            str_roll, ", ".join(str(r) for r in results), total))
