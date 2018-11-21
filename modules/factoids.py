import re
from src import ModuleManager, utils

REGEX_FACTOID = re.compile("{!factoid ([^}]+)}", re.I)

class Module(ModuleManager.BaseModule):
    def _get_factoid(self, server, factoid):
        name = factoid.lower().strip()
        return name, server.get_setting("factoid-%s" % name, None)

    @utils.hook("received.command.factoid", min_args=1)
    def factoid(self, event):
        """
        :help: Set/get a factoid
        :usage: <key> [= value]
        """
        if "=" in event["args"]:
            key, _, value = event["args"].partition("=")
            factoid = key.lower().strip()
            event["server"].set_setting("factoid-%s" % factoid, value.strip())

            event["stdout"].write("Set factoid '%s'" % factoid)
        else:
            name, value = self._get_factoid(event["server"], event["args"])
            if value == None:
                raise utils.EventError("Unknown factoid '%s'" % name)
            event["stdout"].write("%s: %s" % (name, value))

    @utils.hook("received.message.channel")
    def channel_message(self, event):
        match = REGEX_FACTOID.search(event["message"])
        if match:
            name, value = self._get_factoid(event["server"], match.group(1))
            if not value == None:
                self.events.on("send.stdout").call(target=event["channel"],
                    module_name="Factoids", server=event["server"],
                    message="%s: %s" % (name, value))
