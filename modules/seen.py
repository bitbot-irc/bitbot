#--depends-on commands

import time
from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.message.channel")
    def channel_message(self, event):
        seen_seconds = time.time()
        event["user"].set_setting("seen", seen_seconds)

    @utils.hook("received.command.seen", min_args=1)
    def seen(self, event):
        """
        :help: Find out when a user was last seen
        :usage: <nickname>
        """
        seen_seconds = event["server"].get_user(event["args_split"][0]
            ).get_setting("seen")
        if seen_seconds:
            since = utils.to_pretty_time(time.time()-seen_seconds,
                max_units=2)
            event["stdout"].write("%s was last seen %s ago" % (
                event["args_split"][0], since))
        else:
            event["stderr"].write("I have never seen %s before." % (
                event["args_split"][0]))
