from src import ModululeManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.factoid", min_args=1)
    def factoid(self, event):
        if "=" in event["args"]:
            key, _, value = event["args"].partition("=")
            factoid = key.lower().strip()
            event["server"].set_setting("factoid-" % factoid, value.strip())

            event["stdout"].write("Set factoid '%s'" % factoid)
        else:
            factoid = event["args"].lower().strip()
            value = event["server"].get_setting("factoid-%s" % factoid, None)

            if value == None:
                raise utils.EventError("Unknown factoid '%s'" % factoid)
            event["stdout"].write("%s: %s" % (factoid, value))
