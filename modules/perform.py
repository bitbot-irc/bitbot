from src import EventManager, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _execute(self, server):
        commands = server.get_setting("perform", [])
        for i, command in enumerate(commands):
            command = command.split("%%")
            for j, part in enumerate(command[:]):
                command[j] = part.replace("%nick%", server.nickname)
            command = "%".join(command)
            server.send_raw(command)

    @utils.hook("received.001", priority=EventManager.PRIORITY_URGENT)
    def on_connect(self, event):
        self._execute(event["server"])

    @utils.hook("received.command.performadd", min_args=1)
    def perform_add(self, event):
        """
        :help: Add command to be executed on connect
        :usage: <raw command>
        :permission: perform
        """
        perform = event["server"].get_setting("perform", [])
        perform.append(event["args"])
        event["server"].set_setting("perform", perform)
        event["stdout"].write("Added command")

    @utils.hook("received.command.performexecute")
    def perform_execute(self, event):
        """
        :help: Execute all saved commands
        :permission: perform
        """
        self._execute(event["server"])
