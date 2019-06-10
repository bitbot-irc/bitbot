import re
from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _get_filters(self, server, target):
        filters = server.get_setting("message-filters", [])
        filters.extend(target.get_setting("message-filters", []))
        return list(set(filters))

    @utils.hook("preprocess.send.privmsg")
    @utils.hook("preprocess.send.notice")
    def channel_message(self, event):
        message = event["line"].args[1]
        target_name = event["line"].args[0]

        # strip off any STATUSMSG chars
        target_name = target_name.strip("".join(event["server"].statusmsg))

        if target_name in event["server"].channels:
            target = event["server"].channels.get(target_name)
        else:
            target = event["server"].get_user(target_name)

        filters = self._get_filters(event["server"], target)
        for filter in filters:
            if re.search(filter, message):
                event["line"].invalidate()
                break

    def _filter(self, target, args):
        subcommand = args[0]
        arg = args[1] if len(args) > 1 else None

        message_filters = target.get_setting("message-filters", [])
        if subcommand == "list":
            if not arg:
                return "%d filters in place" % len(message_filters)
            else:
                index = int(arg)
                return "Filter %d: %s" % (index, message_filters[index])
        elif subcommand == "add":
            if arg == None:
                raise TypeError()
            message_filters = set(message_filters)
            message_filters.add(arg)
            target.set_setting("message-filters", list(message_filters))
            return "Added filter"
        elif subcommand == "remove":
            if arg == None:
                raise TypeError()

            index = int(arg)
            message_filters = list(message_filters)
            filter = message_filters.pop(index)
            target.set_setting("message-filters", message_filters)
            return "Removed filter: %s" % filter
        else:
            return None

    @utils.hook("received.command.cfilter", min_args=1)
    def cfilter(self, event):
        """
        :help: Add a message filter for the current channel
        :usage: list
        :usage: add <regex>
        :usage: remove <index>
        :permission: cfilter
        """
        # mark output as "assured" to it can bypass filtering
        event["stdout"].assure()
        event["stderr"].assure()

        try:
            out = self._filter(event["target"], event["args_split"])
            event["stdout"].write(out)
        except TypeError as e:
            event["stderr"].write("Please provide an argument")
        except ValueError:
            event["stderr"].write("Indexes must be numbers")
        except IndexError:
            event["stderr"].write("Unknown index")
