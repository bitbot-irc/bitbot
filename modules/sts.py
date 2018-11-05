import time
from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _get_policy(self, server):
        return server.get_setting("sts-policy", None)
    def _set_policy(self, server, policy):
        self.log.trace("Setting STS policy for '%s': %s", [str(server), policy])
        server.set_setting("sts-policy", policy)
    def _remove_policy(self, server):
        server.del_setting("sts-policy")

    def set_policy(self, server, port, duration):
        expiration = None
        self._set_policy(server, {
            "port": port,
            "from": time.time(),
            "duration": duration})
    def change_duration(self, server, info):
        duration = int(info["duration"])
        if duration == 0:
            self._remove_policy(server)
        else:
            port = server.connection_params.port
            if "port" in info:
                port = int(info["port"])
            self.set_policy(server, port, duration)

    def _get_sts(self, capabilities):
        return capabilities.get("sts", capabilities.get("draft/sts", None))

    @utils.hook("received.cap.ls")
    def on_cap_ls(self, event):
        sts = self._get_sts(event["capabilities"])
        if sts:
            info = utils.parse.keyvalue(sts, delimiter=",")
            if not event["server"].connection_params.tls:
                self.set_policy(event["server"], int(info["port"]), None)
                event["server"].disconnect()
                self.bot.reconnect(event["server"].id,
                    event["server"].connection_params)
            else:
                self.change_duration(event["server"], info)

    @utils.hook("received.cap.new")
    def on_cap_new(self, event):
        sts = self._get_sts(event["capabilities"])
        if sts and event["server"].connection_params.tls:
            info = utils.parse.keyvalue(sts, delimiter=",")
            self.change_duration(event["server"], info)

    @utils.hook("new.server")
    def new_server(self, event):
        sts_policy = self._get_policy(event["server"])
        if sts_policy:
            if not event["server"].connection_params.tls:
                if not sts_policy["duration"] or time.time() <= (
                        sts_policy["from"]+sts_policy["duration"]):
                    self.log.trace("Applying STS policy for '%s'",
                        [str(event["server"])])
                    event["server"].connection_params.tls = True
                    event["server"].connection_params.port = sts_policy["port"]

    @utils.hook("server.disconnect")
    def on_disconnect(self, event):
        sts_policy = self._get_policy(event["server"])
        if sts_policy and sts_policy["duration"]:
            sts_policy["from"] = time.time()
            self._set_policy(event["server"], sts_policy)
