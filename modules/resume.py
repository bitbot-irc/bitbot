from src import ModuleManager, utils

CAP = "draft/resume-0.2"

class Module(ModuleManager.BaseModule):
    def _get_token(self, server):
        return server.connection_params.args.get("resume", [None, None])

    @utils.hook("received.cap.ls")
    def on_cap_new(self, event):
        username, token = self._get_token(event["server"])
        if CAP in event["capabilities"] and (not username or not token):
            event["server"].queue_capability("draft/resume-0.2")

    @utils.hook("received.cap.ack")
    def on_cap_ack(self, event):
        username, token = self._get_token(event["server"])
        if CAP in event["capabilities"] and username and token:
            event["server"].send("RESUME %s %s" % (username, token))
            event["server"].cap_started = False

    @utils.hook("received.resume")
    def on_resume(self, event):
        if event["args"][0] == "SUCCESS":
            self.log.info("Successfully resumed session")
        elif event["args"][0] == "ERR":
            self.log.info("Failed to resume session: %s" % event["args"][1])
        elif event["args"][0] == "TOKEN":
            event["server"].connection_params.args["new-token"
                ] = event["args"][1]

    @utils.hook("received.numeric.001")
    def on_connect(self, event):
        new_token = event["server"].connection_params.args.get("new-token",
            None)
        if new_token:
            event["server"].connection_params.args["resume"] = [
                event["server"].nickname, new_token]
            del event["server"].connection_params.args["resume"]
