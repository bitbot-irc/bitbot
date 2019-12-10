from src import ModuleManager, utils

def _parse(value):
    lines, _, seconds = value.partition(":")
    if lines.isdigit() and seconds.isdigit():
        return [int(lines), int(seconds)]
    return None

@utils.export("serverset", utils.FunctionSetting(_parse, "throttle",
    "Configure lines:seconds throttle for the current server", example="4:2"))
class Module(ModuleManager.BaseModule):
    @utils.hook("received.001")
    def connect(self, event):
        throttle = event["server"].get_setting("throttle", None)
        if throttle:
            lines, seconds = throttle
            event["server"].socket.set_throttle(lines, seconds)
