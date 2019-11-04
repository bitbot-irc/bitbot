#--depends-on commands
#--depends-on format_activity

import time
from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _change_seen(self, channel, user, action):
        user.set_setting("seen", time.time())
        channel.set_user_setting(user.get_id(), "seen-info", {"action": action})

    @utils.hook("formatted.message.channel")
    @utils.hook("formatted.notice.channel")
    def on_formatted(self, event):
        line = event["minimal"] or event["line"]

        if event["channel"]:
            self._change_seen(event["channel"], event["user"], line)
        elif event["user"]:
            for channel in event["user"].channels:
                self._change_seen(channel, event["user"], line)

    @utils.hook("received.command.seen", min_args=1)
    def seen(self, event):
        """
        :help: Find out when a user was last seen
        :usage: <nickname>
        """
        user = event["server"].get_user(event["args_split"][0])
        seen_seconds = user.get_setting("seen")

        if seen_seconds:
            seen_info = None
            if event["is_channel"]:
                seen_info = event["target"].get_user_setting(
                    user.get_id(), "seen-info", None)
                if seen_info:
                    seen_info = " (%s%s)" % (seen_info["action"],
                        utils.consts.RESET)

            since = utils.to_pretty_time(time.time()-seen_seconds,
                max_units=2)
            event["stdout"].write("%s was last seen %s ago%s" % (
                event["args_split"][0], since, seen_info or ""))
        else:
            event["stderr"].write("I have never seen %s before." % (
                event["args_split"][0]))
