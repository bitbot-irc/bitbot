#--depends-on commands

import re
from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    _name = "Filter"

    def _split(self, s):
        backslash = False
        forward_slash = []
        for i, c in enumerate(s):
            if not backslash:
                if c == "/":
                    forward_slash.append(i)
                if c == "\\":
                    backslash = True
            else:
                backslash = False
        if forward_slash and (not forward_slash[-1] == (len(s)-1)):
            forward_slash.append(len(s))

        last = 0
        out = []
        for i in forward_slash:
            out.append(s[last:i])
            last = i+1
        return out

    def _get_filters(self, server, target):
        filters = server.get_setting("message-filters", [])
        filters.extend(target.get_setting("message-filters", []))
        return list(set(filters))

    @utils.hook("preprocess.send.privmsg")
    @utils.hook("preprocess.send.notice")
    def channel_message(self, event):
        message = event["line"].args[1]
        message_plain = utils.irc.strip_font(message)
        original_message = message
        target_name = event["line"].args[0]

        # strip off any STATUSMSG chars
        target_name = target_name.strip("".join(event["server"].statusmsg))

        if target_name in event["server"].channels:
            target = event["server"].channels.get(target_name)
        else:
            target = event["server"].get_user(target_name)

        filters = self._get_filters(event["server"], target)
        for filter in filters:
            type, pattern, *args = self._split(filter)
            if type == "m":
                if re.search(pattern, message_plain):
                    self.log.info("Message matched filter, dropping: %s"
                        % event["line"].format())
                    event["line"].invalidate()
                    return
            elif type == "s":
                replace, *args = args
                message = re.sub(pattern, replace, message)
        if not message == message_plain:
            event["line"].args[1] = message

    @utils.hook("received.command.cfilter", min_args=1)
    @utils.kwarg("help", "Add a message filter for the current channel")
    @utils.kwarg("permissions", "cfilter")
    @utils.spec("!'list ?<index>int")
    @utils.spec("!'add ?<m/pattern/>string|<s/pattern/replace/>string")
    @utils.spec("!'remove !<index>int")
    def cfilter(self, event):
        # mark output as "assured" so it can bypass filtering
        event["stdout"].assure()
        event["stderr"].assure()
        target = event["target"]
        filters = target.get_setting("message-filters", [])

        if event["spec"][0] == "list":
            if event["spec"][1]:
                if not len(filters) > event["spec"][1]:
                    raise utils.EventError("Filter index %d doesn't exist"
                        % event["spec"][1])
                event["stdout"].write("Message filter %d: %s"
                    % (event["spec"][1], filters[event["spec"][1]]))
            else:
                s = ", ".join(
                    f"({i}) {s}" for i, s in enumerate(filters))
                event["stdout"].write("Message filters: %s" % s)

        elif event["spec"][0] == "add":
            filters.append(event["spec"][1])
            target.set_setting("message-filters", filters)
            event["stdout"].write("Added filter %d" % (len(filters)-1))

        elif event["spec"][0] == "remove":
            if not filters:
                raise utils.EventError("No filters")

            removed = filters.pop(event["spec"][1])
            target.set_setting("message-filters", filters)
            event["stdout"].write("Removed filter %d: %s" %
                (event["spec"][1], removed))
