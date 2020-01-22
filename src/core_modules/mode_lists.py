from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    # RPL_BANLIST
    @utils.hook("received.367")
    def on_367(self, event):
        self._mode_list_mask(event["server"], event["line"].args[1], "b",
            event["line"].args[2])
    @utils.hook("received.368")
    def on_368(self, event):
        self._mode_list_end(event["server"], event["line"].args[1], "b")

    # RPL_QUIETLIST
    @utils.hook("received.728")
    def on_728(self, event):
        self._mode_list_mask(event["server"], event["line"].args[1], "q",
            event["line"].args[3])
    @utils.hook("received.729")
    def on_729(self, event):
        self._mode_list_end(event["server"], event["line"].args[1], "q")

    def _mode_list_mask(self, server, target, mode, mask):
        if target in server.channels:
            channel = server.channels.get(target)
            self._mask_add(channel, "~%s " % mode, mask)
    def _mode_list_end(self, server, target, mode):
        if target in server.channels:
            channel = server.channels.get(target)
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

