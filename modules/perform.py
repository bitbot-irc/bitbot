from src import EventManager, ModuleManager, Utils

class Module(ModuleManager.BaseModule):
    @Utils.hook("received.numeric.001", priority=EventManager.PRIORITY_URGENT)
    def on_connect(self, event):
        commands = event["server"].get_setting("perform", [])
        for i, command in enumerate(commands):
            command = command.split("%%")
            for j, part in enumerate(command[:]):
                command[j] = part.replace("%nick%", event["server"
                    ].original_nickname)
            command = "%".join(command)
            event["server"].send(command)
