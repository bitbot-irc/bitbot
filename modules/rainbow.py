import random
from src import ModuleManager, utils

COLORS = [
    utils.consts.BLUE,
    utils.consts.LIGHTBLUE,
    utils.consts.CYAN,
    utils.consts.LIGHTCYAN,
    utils.consts.GREEN,
    utils.consts.LIGHTGREEN,
    utils.consts.YELLOW,
    utils.consts.ORANGE,
    utils.consts.BROWN,
    utils.consts.RED,
    utils.consts.PINK,
    utils.consts.PURPLE
]

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.rainbow")
    @utils.kwarg("help", "Rainbowify a given string or the last message")
    @utils.kwarg("usage", "[string]")
    def rainbow(self, event):
        args = event["args"]
        if not args:
            args = event["target"].buffer.get()
            if not args:
                raise utils.EventError("No line found to rainbowify")

        offset = random.randint(0, len(COLORS))
        out = ""
        for i, c in enumerate(event["args"]):
            color = COLORS[(i+offset)%len(COLORS)]
            out += utils.irc.color(c, color, terminate=False)
        event["stdout"].write(out)
