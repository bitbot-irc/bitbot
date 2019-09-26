#--depends-on commands

import random, re
from src import ModuleManager, utils

ERROR_FORMAT = "Incorrect format! Format must be [number]d[number], e.g. 1d20"
RE_DICE = re.compile("([1-9]\d*)d([1-9]\d*)((?:[-+]\d+)*)", re.I)
RE_MODIFIERS = re.compile("([-+]\d+)")

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.roll", min_args=1)
    @utils.hook("received.command.dice", alias_of="roll")
    def roll_dice(self, event):
        """
        :help: Roll some dice, DND style
        :usage: [1-6]d[1-30]
        """
        match = RE_DICE.match(event["args_split"][0])
        if match:
            roll = match.group(0)
            dice_count = int(match.group(1))
            side_count = int(match.group(2))
            modifiers = RE_MODIFIERS.findall(match.group(3))

            if dice_count > 6:
                raise utils.EventError("Max number of dice is 6")
            if side_count > 30:
                raise utils.EventError("Max number of sides is 30")

            results = random.choices(range(1, side_count+1), k=dice_count)

            total_n = sum(results)
            for modifier in modifiers:
                if modifier[0] == "+":
                    total_n += int(modifier[1:])
                else:
                    total_n -= int(modifier[1:])

            total = ""
            if len(results) > 1:
                total = " (total: %d)" % total_n

            results_str = ", ".join(str(r) for r in results)
            event["stdout"].write("Rolled %s and got %s%s" % (
                roll, results_str, total))
