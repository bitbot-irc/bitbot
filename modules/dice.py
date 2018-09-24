import random
from src import Utils

class Module(object):
    def __init__(self, bot, events, exports):
        events.on("received.command.roll").hook(
            self.roll_dice,
            min_args=1,
            help="Roll some dice, DND style!",
            usage="[1-5]d[1-20]"
        )

        self.err_msg = "Incorrectly formatted dice! Format must be [number]d[number], for example, 1d20"

    def roll_dice(self, event):
        raw_input = event["args_split"][0]
        roll = raw_input.split("d")
        results = []

        if len(roll) is not 2:
            event["stderr"].write(self.err_msg)
            return

        if roll[0].isdigit() is False or roll[1].isdigit() is False:
            event["stderr"].write(self.err_msg)
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
