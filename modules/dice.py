#--depends-on commands

import random, re
from src import ModuleManager, utils

ERROR_FORMAT = "Incorrect format! Format must be [number]d[number], e.g. 1d20"
RE_DICE = re.compile("^([1-9]\d*)?d([1-9]\d*)((?:[-+][1-9]\d{,2})*)$", re.I)
RE_MODIFIERS = re.compile("([-+]\d+)")

MAX_DICE = 6
MAX_SIDES = 100

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.roll")
    @utils.hook("received.command.dice", alias_of="roll")
    @utils.kwarg("help", "Roll dice DND-style")
    @utils.kwarg("usage", "[1-%s]d[1-%d]" % (MAX_DICE, MAX_SIDES))
    def roll_dice(self, event):
        args = None
        if event["args_split"]:
            args = event["args_split"][0]
        else:
            args = "1d6"

        match = RE_DICE.match(args)
        if match:
            roll = match.group(0)
            dice_count = int(match.group(1) or "1")
            side_count = int(match.group(2))
            modifiers = RE_MODIFIERS.findall(match.group(3))

            if dice_count > 6:
                raise utils.EventError("Max number of dice is %s" % MAX_DICE)
            if side_count > MAX_SIDES:
                raise utils.EventError("Max number of sides is %s"
                    % MAX_SIDES)

            results = random.choices(range(1, side_count+1), k=dice_count)

            total_n = sum(results)
            for modifier in modifiers:
                if modifier[0] == "+":
                    total_n += int(modifier[1:])
                else:
                    total_n -= int(modifier[1:])

            total = ""
            if len(results) > 1 or modifiers:
                total = " (total: %d)" % total_n

            results_str = ", ".join(str(r) for r in results)
            event["stdout"].write("Rolled %s and got %s%s" % (
                roll, results_str, total))
        else:
            event["stderr"].write("Invalid format. Example: 2d12+2")
