from src import EventManager, ModuleManager, utils

# Strip magic whitespace string from the end of messages.
# OTR uses this string to advertise, over plaintext, that the sending user
# supports OTR.

MAGIC = " \t  \t\t\t\t \t \t \t    \t\t  \t \t"

class Module(ModuleManager.BaseModule):
    @utils.hook("raw.received.privmsg")
    @utils.kwarg("priority", EventManager.PRIORITY_HIGH)
    def on_message(self, event):
        message = event["line"].args.get(1)
        if message.endswith(MAGIC):
            event["line"].args[1] = message.rsplit(MAGIC, 1)[0]
