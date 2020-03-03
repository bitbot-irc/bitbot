from src import EventManager, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("new.user")
    @utils.hook("new.channel")
    def new(self, event):
        obj = event.get("user", event.get("channel", None))
        obj._last_stdout = None
        obj._last_stderr = None

    @utils.hook("postprocess.command")
    @utils.kwarg("priority", EventManager.PRIORITY_MONITOR)
    def postprocess(self, event):
        if event["stdout"].has_text():
            event["target"]._last_stdout = event["stdout"]
        if event["stderr"].has_text():
            event["target"]._last_stderr = event["stderr"]

    @utils.hook("received.command.more")
    def more(self, event):
        last_stdout = event["target"]._last_stdout
        if last_stdout and last_stdout.has_text():
            event["stdout"].copy_from(last_stdout)
