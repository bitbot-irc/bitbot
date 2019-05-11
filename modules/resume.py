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
            cap = utils.irc.Capability(CAP)
            cap.on_ack(lambda: self._cap_ack(event["server"]))
            return cap

    def _cap_ack(self, server):
        server.wait_for_capability("resume")

    @utils.hook("received.resume")
    def on_resume(self, event):
        cap_done = True

        if event["args"][0] == "SUCCESS":
            resume_channels = event["server"].get_setting("resume-channels", [])
            self.log.info("Successfully resumed session", [])
            event["server"].cap_started = False

        elif event["args"][0] == "ERR":
            self.log.info("Failed to resume session: %s", [event["args"][1]])

        elif event["args"][0] == "TOKEN":
            token = self._get_token(event["server"])
            self._set_token(event["server"], event["args"][1], new=True)

            if token:
                timestamp = event["server"]._resume_timestamp

                event["server"].send_raw("RESUME %s%s" %
                    (token, " %s" % timestamp if timestamp else ""))
                cap_done = False

        if cap_done:
            event["server"].capability_done("resume")


    @utils.hook("received.001")
    def on_connect(self, event):
        event["server"].del_setting("resume-channels")

        new_token = self._get_token(event["server"], new=True)
        if new_token:
            self._set_token(event["server"], new_token)
            self._del_token(event["server"], new=True)

    @utils.hook("self.join")
    def on_join(self, event):
        resume_channels = event["server"].get_setting("resume-channels", [])
        channel_name = event["server"].irc_lower(event["channel"].name)
        if not channel_name in resume_channels:
            resume_channels.append(channel_name)
            event["server"].set_setting("resume-channels", resume_channels)
