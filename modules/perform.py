

class Module(object):
    def __init__(self, bot):
        bot.events.on("received").on("numeric").on("001").hook(
            self.on_connect)

    def on_connect(self, event):
        commands = event["server"].get_setting("perform", [])
        for i, command in enumerate(commands):
            command = command.split("%%")
            for j, part in enumerate(command[:]):
                command[j] = part.replace("%nick%", event["server"
                    ].original_nickname)
            command = "%".join(command)
            event["server"].send(command)
