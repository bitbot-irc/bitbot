from src import ModuleManager, utils

class ThrottleSetting(utils.Setting):
    def parse(self, value):
        lines, _, seconds = value.partition(":")
        if lines.isdigit() and seconds.isdigit():
            return [int(lines), int(seconds)]
        return None

@utils.export("serverset", ThrottleSetting("throttle",
    "Configure lines:seconds throttle for the current server", example="4:2"))
class Module(ModuleManager.BaseModule):
    @utils.hook("received.001")
    def connect(self, event):
        throttle = event["server"].get_setting("throttle", None)
        if throttle:
            lines, seconds = throttle
            event["server"].socket.set_throttle(lines, seconds)
