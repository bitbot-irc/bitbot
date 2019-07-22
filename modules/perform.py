#--depends-on commands
#--depends-on permissions

from src import EventManager, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _execute(self, server, commands, **kwargs):
        for command in commands:
            server.send_raw(command.format(**kwargs))

    @utils.hook("received.001", priority=EventManager.PRIORITY_URGENT)
    def on_connect(self, event):
        commands = event["server"].get_setting("perform", [])
        self._execute(event["server"], commands, NICK=event["server"].nickname)

    @utils.hook("self.join", priority=EventManager.PRIORITY_URGENT)
    def on_join(self, event):
        commands = event["channel"].get_setting("perform", [])
        self._execute(event["server"], commands, NICK=event["server"].nickname,
            CHAN=event["channel"].name)

    def _perform(self, target, args_split):
        subcommand = args_split[0].lower()
        current_perform = target.get_setting("perform", [])
        if subcommand == "list":
            return "Configured commands: %s" % ", ".join(current_perform)

        message = None
        if subcommand == "add":
            if not len(args_split) > 1:
                raise utils.EventError("Please provide a raw command to add")
            current_perform.append(" ".join(args_split[1:]))
            message = "Added command"
        elif subcommand == "remove":
            if not len(args_split) > 1:
                raise utils.EventError("Please provide an index to remove")
            if not args_split[1].isdigit():
                raise utils.EventError("Please provide a number")
            index = int(args_split[1])
            if not index < len(current_perform):
                raise utils.EventError("Index out of bounds")
            current_perform.pop(index)
            message = "Removed command"
        else:
            raise utils.EventError("Unknown subcommand '%s'" % subcommand)

        target.set_setting("perform", current_perform)
        return message

    @utils.hook("received.command.perform", min_args=1)
    @utils.kwarg("min_args", 1)
    @utils.kwarg("help", "Edit on-connect command configuration")
    @utils.kwarg("usage", "list")
    @utils.kwarg("usage", "add <raw command>")
    @utils.kwarg("usage", "remove <index>")
    @utils.kwarg("permission", "perform")
    def perform(self, event):
        event["stdout"].write(self._perform(event["server"],
            event["args_split"]))

    @utils.hook("received.command.cperform", min_args=1)
    @utils.kwarg("min_args", 1)
    @utils.kwarg("channel_only", True)
    @utils.kwarg("help", "Edit channel on-join command configuration")
    @utils.kwarg("usage", "list")
    @utils.kwarg("usage", "add <raw command>")
    @utils.kwarg("usage", "remove <index>")
    @utils.kwarg("permission", "cperform")
    def cperform(self, event):
        event["stdout"].write(self._perform(event["target"],
            event["args_split"]))
