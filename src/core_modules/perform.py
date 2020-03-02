#--depends-on commands
#--depends-on permissions

from src import EventManager, IRCLine, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _execute(self, server, commands, **kwargs):
        for command in commands:
            line = command.format(**kwargs)
            if IRCLine.is_human(line):
                line = IRCLine.parse_human(line)
            else:
                line = IRCLine.parse_line(line)
            server.send(line)

    @utils.hook("received.001", priority=EventManager.PRIORITY_URGENT)
    def on_connect(self, event):
        commands = event["server"].get_setting("perform", [])
        self._execute(event["server"], commands, NICK=event["server"].nickname)

    @utils.hook("self.join", priority=EventManager.PRIORITY_URGENT)
    def on_join(self, event):
        commands = event["channel"].get_setting("perform", [])
        self._execute(event["server"], commands, NICK=event["server"].nickname,
            CHAN=event["channel"].name)

    def _perform(self, target, spec):
        subcommand = spec[0]
        current_perform = target.get_setting("perform", [])
        if subcommand == "list":
            return "Configured commands: %s" % ", ".join(current_perform)

        message = None
        if subcommand == "add":
            current_perform.append(spec[1])
            message = "Added command"
        elif subcommand == "remove":
            index = spec[1]
            if not index < len(current_perform):
                raise utils.EventError("Index out of bounds")
            command = current_perform.pop(index)
            message = "Removed command %d (%s)" % (index, command)

        target.set_setting("perform", current_perform)
        return message

    @utils.hook("received.command.perform", permission="perform",
        help="Edit on-connect command configuration")
    @utils.hook("received.command.cperform", permission="perform",
        help="Edit channel on-join command configuration", channel_only=True)
    @utils.kwarg("help", "Edit on-connect command configuration")
    @utils.spec("!'list")
    @utils.spec("!'add !<command>string")
    @utils.spec("!'remove !<index>int")
    def perform(self, event):
        if event["command"] == "perform":
            target = event["server"]
        elif event["command"] == "cperform":
            target = event["target"]

        out = self._perform(target, event["spec"])
        event["stdout"].write("%s: %s" % (event["user"].nickname, out))
