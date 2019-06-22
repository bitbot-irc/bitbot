from src import EventManager, ModuleManager, utils

# postpone parsing SOME lines until after 001

class Module(ModuleManager.BaseModule):
    @utils.hook("new.server")
    def new_server(self, event):
        event["server"]._deferred_read = []

    @utils.hook("raw.received.001", priority=EventManager.PRIORITY_LOW)
    def on_001(self, event):
        lines = event["server"]._deferred_read[:]
        event["server"]._deferred_read.clear()
        for line in lines:
            self.events.on("raw.received").call(line=line,
                server=event["server"])

    @utils.hook("raw.received.mode", priority=EventManager.PRIORITY_HIGH)
    def defer(self, event):
        if not event["server"].connected:
            event.eat()
            event["server"]._deferred_read.append(event["line"])

