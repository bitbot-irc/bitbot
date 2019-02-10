from src import ModuleManager, utils

CAP = "draft/resume-0.2"

class Module(ModuleManager.BaseModule):
    def _get_token(self, server):
        return server.connection_params.args.get("resume-token", (None, None))
    def _set_token(Self, server, nickname, token):
        server.connection_params.args["resume-token"] = (nickname, token)

    @utils.hook("received.cap.ls")
    def on_cap_ls(self, event):
        nickname, token = self._get_token(event["server"])
        if CAP in event["capabilities"]:
            event["server"].queue_capability(CAP)

    @utils.hook("received.cap.ack")
    def on_cap_ack(self, event):
        event["server"].wait_for_capability("resume")

    @utils.hook("received.resume")
    def on_resume(self, event):
        if event["args"][0] == "SUCCESS":
            self.log.info("Successfully resumed session", [])
        elif event["args"][0] == "ERR":
            self.log.info("Failed to resume session: %s", [event["args"][1]])
        elif event["args"][0] == "TOKEN":
            event["server"].connection_params.args["new-resume-token"
                ] = event["args"][1]
            nickname, token = self._get_token(event["server"])

            if nickname and token:
                event["server"].send("RESUME %s %s" % (nickname, token))
                event["server"].capability_done("resume")

    @utils.hook("received.numeric.001")
    def on_connect(self, event):
        new_token = event["server"].connection_params.args.get(
            "new-resume-token", None)
        if new_token:
            self._set_token(event["server"], event["server"].nickname,
                new_token)
            del event["server"].connection_params.args["new-resume-token"]

    @utils.hook("self.nick")
    def nick_change(self, event):
        nickname, token = self._get_token(event["server"])
        if nickname and token:
            self._set_token(event["server"], event["new_nickname"], token)
