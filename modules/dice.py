import random
from src import ModuleManager, Utils

ERROR_FORMAT = "Incorrect format! Format must be [number]d[number], e.g. 1d20"

class Module(ModuleManager.BaseModule):
    @Utils.hook("received.command.roll", min_args=1, usage="[1-5]d[1-20]")
    def roll_dice(self, event):
        """
        Roll some dice, DND style!
        """
        raw_input = event["args_split"][0]
        roll = raw_input.split("d")
        results = []

        if len(roll) is not 2:
            event["stderr"].write(ERROR_FORMAT)
            return

        if roll[0].isdigit() is False or roll[1].isdigit() is False:
            event["stderr"].write(ERROR_FORMAT)
            return

        roll = [int(roll[0]), int(roll[1])]

        num_of_die = 5 if roll[0] > 5 else roll[0]
        sides_of_die = 20 if roll[1] > 20 else roll[1]

        str_roll = str(num_of_die) + "d" + str(sides_of_die)

        for i in range(0, num_of_die):
            results.append(random.randint(1, sides_of_die))

        total = sum(results)
        results = ', '.join(map(str, results))

        event["stdout"].write("Rolled " + Utils.bold(str_roll) + " for a total "
                              + "of " + Utils.bold(str(total))
                              + ": " + results)
