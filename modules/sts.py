import time
from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def _set_policy(self, server, port, duration, one_shot):
        expiration = None
        if duration:
            expiration = time.time()+int(duration)
        server.set_setting("sts-policy", {
            "port": port,
            "expiration": expiration,
            "one-shot": one_shot})
    def _change_duration(self, server, info):
        port = event["server"].port
        if "port" in info:
            port = int(info["port"])
        self._set_policy(server, port, info["duration"], False)

    @utils.hook("received.cap.ls")
    def on_cap_ls(self, event):
        has_sts = "sts" in event["capabilities"]
        if "sts" in event["capabilities"]:
            info = utils.parse.keyvalue(event["capabilities"]["sts"],
                delimiter=",")
            if not event["server"].tls:
                self._set_policy(event["server"], int(info["port"]),
                    None, True)
                event["server"].disconnect()
            else:
                self._change_duration(event["server"], info)

    @utils.hook("received.cap.new")
    def on_cap_new(self, event):
        if "sts" in event["capabilities"] and event["server"].tls:
            info = utils.parse.keyvalue(event["capabilities"]["sts"],
                delimiter=",")
            if event["server"].tls:
                self._change_duration(event["server"], info)

    @utils.hook("new.server")
    def new_server(self, event):
        sts_policy = event["server"].get_setting("sts-policy")
        if sts_policy:
            if sts_policy["one-shot"]:
                event["server"].del_setting("sts-policy")
            if not event["server"].tls:
                expiration = sts_policy["expiration"]
                if not expiration or time.time() <= expiration:
                    self.log.debug("Applying STS policy for '%s'",
                        [str(event["server"])])
                    event["server"].tls = True
                    event["server"].port = sts_policy["port"]
