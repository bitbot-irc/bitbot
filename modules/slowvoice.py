#--depends-on config

from src import ModuleManager, utils

DELAY = 30 # 30 seconds

@utils.export("channelset", utils.BoolSetting("slowvoice",
    "Enable/disable giving +v to new users after a delay"))
@utils.export("channelset", utils.IntSetting("slowvoice-delay",
    "Set delay for slowvoice in seconds"))
class Module(ModuleManager.BaseModule):
    @utils.hook("timer.slowvoice")
    def timer(self, event):
        event["channel"].send_mode("+v", [event["user"].nickname])

    @utils.hook("new.channel")
    def new_channel(self, event):
        event["channel"]._slowvoice_timers = {}

    @utils.hook("received.join")
    def on_join(self, event):
        if event["channel"].get_setting("slowvoice", False):
            delay = event["channel"].get_setting("slowvoice-delay", DELAY)
            timer = self.timers.add("slowvoice", delay,
                channel=event["channel"], user=event["user"])
            event["channel"]._slowvoice_timers[event["user"]] = timer

    def _cancel_timer(self, user, channel):
        if user in channel._slowvoice_timers:
            timer = channel._slowvoice_timers.pop(user)
            timer.cancel()

    @utils.hook("received.part")
    def on_part(self, event):
        self._cancel_timer(event["user"], event["channel"])

    @utils.hook("received.quit")
    def on_quit(self, event):
        for channel in event["user"].channels:
            self._cancel_timer(event["user"], channel)

    @utils.hook("self.part")
    def self_part(self, event):
        event["channel"]._slowvoice_timers.clear()
