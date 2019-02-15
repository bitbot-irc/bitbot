from src import ModuleManager, utils

CAP = "draft/resume-0.3"

class Module(ModuleManager.BaseModule):
    def _setting(self, new):
        return "resume-token%s" % ("-new" if new else "")
    def _get_token(self, server, new=False):
        return server.get_setting(self._setting(new), None)
    def _set_token(self, server, token, new=False):
        server.set_setting(self._setting(new), token)
    def _del_token(self, server, new=False):
        server.del_setting(self._setting(new))

    def _get_timestamp(self, server):
        return server.get_setting("last-read", None)

    @utils.hook("new.server")
    def new_server(self, event):
        resume_timestamp = self._get_timestamp(event["server"])
        event["server"]._resume_timestamp = resume_timestamp

    @utils.hook("received.cap.ls")
    def on_cap_ls(self, event):
        if CAP in event["capabilities"]:
            event["server"].queue_capability(CAP)

    @utils.hook("received.cap.ack")
    def on_cap_ack(self, event):
        if CAP in event["capabilities"]:
            event["server"].wait_for_capability("resume")

    @utils.hook("received.resume")
    def on_resume(self, event):
        if event["args"][0] == "SUCCESS":
            self.log.info("Successfully resumed session", [])

        elif event["args"][0] == "ERR":
            self.log.info("Failed to resume session: %s", [event["args"][1]])

        elif event["args"][0] == "TOKEN":
            token = self._get_token(event["server"])
            self._set_token(event["server"], event["args"][1], new=True)

            if token:
                timestamp = event["server"]._resume_timestamp

                event["server"].send("RESUME %s%s" %
                    (token, " %s" % timestamp if timestamp else ""))
                event["server"].cap_started = False

        event["server"].capability_done("resume")

    @utils.hook("received.numeric.001")
    def on_connect(self, event):
        new_token = self._get_token(event["server"], new=True)
        if new_token:
            self._set_token(event["server"], new_token)
            self._del_token(event["server"], new=True)
