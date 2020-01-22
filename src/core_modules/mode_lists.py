from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    # RPL_BANLIST
    @utils.hook("received.367")
    def on_367(self, event):
        self._mode_list_mask(event, "b", event["line"].args[2])
    @utils.hook("received.368")
    def on_368(self, event):
        self._mode_list_end(event, "b")

    # RPL_QUIETLIST
    @utils.hook("received.728")
    def on_728(self, event):
        self._mode_list_mask(event, "q", event["line"].args[3])
    @utils.hook("received.729")
    def on_729(self, event):
        self._mode_list_end(event, "q")


    def _excepts(self, server):
        return server.isupport.get("EXCEPTS", None) or "e"
    # RPL_EXCEPTLIST
    @utils.hook("received.348")
    def on_348(self, event):
        mode = self._excepts(event["server"])
        self._mode_list_mask(event, mode, event["line"].args[3])
    @utils.hook("received.349")
    def on_349(self, event):
        self._mode_list_end(event, self._excepts(event["server"]))

    def _invex(self, server):
        return server.isupport.get("INVEX", None) or "I"
    # RPL_INVITELIST
    @utils.hook("received.346")
    def on_346(self, event):
        mode = self._invex(event["server"])
        self._mode_list_mask(event, mode, event["line"].args[3])
    @utils.hook("received.347")
    def on_347(self, event):
        self._mode_list_end(event, self._invex(event["server"]))

    def _channel(self, event):
        target = event["line"].args[1]
        if target in event["server"].channels:
            return event["server"].channels.get(target)
        return None

    def _mode_list_mask(self, event, mode, mask):
        channel = self._channel(event)
        if channel:
            self._mask_add(channel, "~%s" % mode, mask)
    def _mode_list_end(self, event, mode):
        channel = self._channel(event)
        if channel:
            temp_key = "~%s" % mode
            if temp_key in channel.mode_lists:
                channel.mode_lists[mode] = channel.mode_lists.pop(temp_key)
            else:
                channel.mode_lists[mode] = set([])

    def _mask_add(self, channel, mode, mask):
        if not mode in channel.mode_lists:
            channel.mode_lists[mode] = set([])
        channel.mode_lists[mode].add(mask)
    def _mask_remove(self, channel, mode, mask):
        if mode in channel.mode_lists:
            channel.mode_lists[mode].discard(mask)

    @utils.hook("received.mode.channel")
    def channel_mode_lists(self, event):
        for mode, arg in event["modes"]:
            if mode[1] in event["server"].channel_list_modes:
                if mode[0] == "+":
                    self._mask_add(event["channel"], mode[1], arg)
                else:
                    self._mask_remove(event["channel"], mode[1], arg)
            elif mode[1] in dict(event["server"].prefix_modes):
                if event["server"].irc_equals(event["server"].nickname, arg):
                    missed = set(event["server"].channel_list_modes)-set(
                        event["channel"].mode_lists.keys())
                    if missed:
                        event["channel"].send_mode("+%s" % "".join(missed))

    @utils.hook("self.join")
    def self_join(self, event):
        event["channel"].send_mode("+%s" %
            "".join(event["server"].channel_list_modes))

