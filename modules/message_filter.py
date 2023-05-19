#--depends-on commands

import re
from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    _name = "Filter"

    def _get_filters(self, server, target):
        filters = self.bot.get_setting("message-filters", [])
        filters.extend(server.get_setting("message-filters", []))
        filters.extend(target.get_setting("message-filters", []))
        return list(set(filters))

    @utils.hook("preprocess.send.privmsg")
    @utils.hook("preprocess.send.notice")
    def channel_message(self, event):
        if event["line"].assured():
            # don't run filters/replaces against assured lines
            return

        message = event["line"].args[1]
        original_message = message
        message_plain = utils.irc.strip_font(message)
        target_name = event["line"].args[0]

        # strip off any STATUSMSG chars
        target_name = target_name.strip("".join(event["server"].statusmsg))

        if target_name in event["server"].channels:
            target = event["server"].channels.get(target_name)
        else:
            target = event["server"].get_user(target_name)

        filters = self._get_filters(event["server"], target)
        for filter in filters:
            sed = utils.parse.sed.parse(filter)

            if sed.type == "m":
                out = utils.parse.sed.sed(sed, message_plain)
                if out:
                    self.log.info("Message matched filter, dropping: %s"
                        % event["line"].format())
                    event["line"].invalidate()
                    return
            elif sed.type == "s":
                out = utils.parse.sed.sed(sed, message)
                message = out

        if not message == original_message:
            event["line"].args[1] = message

    @utils.hook("received.command.cfilter", channel_only=True,
        require_access="high,filter", require_mode="o")
    @utils.hook("received.command.filter")
    @utils.hook("received.command.bfilter")
    @utils.kwarg("help", "Add a message filter for the current channel")
    @utils.kwarg("permission", "cfilter")
    @utils.spec("!'list ?<index>int")
    @utils.spec("!'add ?<m/pattern/>string|<s/pattern/replace/>string")
    @utils.spec("!'remove !<index>int")
    def filter(self, event):
        # mark output as "assured" so it can bypass filtering
        event["stdout"].assure()
        event["stderr"].assure()

        if event["command"] == "cfilter":
            target = event["target"]
        elif event["command"] == "bfilter":
            target = self.bot
        else:
            target = event["server"]
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
