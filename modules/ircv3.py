from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    _name = "IRCv3"

    @utils.hook("received.command.specsup", min_args=1)
    @utils.kwarg("help", "List servers supporting a given IRCv3 capability")
    @utils.kwarg("usage", "<capability>")
    def specsup(self, event):
        spec = event["args_split"][0].lower()
        supporting_servers = []

        for server in self.bot.servers.values():
            if not server.connection_params.hostname == "localhost":
                if spec in server.server_capabilities:
                    port = str(server.connection_params.port)
                    if server.connection_params.tls:
                        port = "+%s" % port
                    supporting_servers.append("%s:%s" % (
                        server.connection_params.hostname, port))
        if supporting_servers:
            event["stdout"].write("%s: %s" % (spec,
                ", ".join(supporting_servers)))
        else:
            event["stderr"].write("No supporting servers found for %s" % spec)

    @utils.hook("received.command.caps")
    @utils.kwarg("help", "List negotiated IRCv3 capabilities")
    def capabilities(self, event):
        event["stdout"].write("IRCv3 capabilities: %s" %
            ", ".join(event["server"].agreed_capabilities))
