from src import ModuleManager, utils

REASON = "User is banned from this channel"

@utils.export("channelset", utils.BoolSetting("ban-enforce",
    "Whether or not to parse new bans and kick who they affect"))
class Module(ModuleManager.BaseModule):
    @utils.hook("received.mode.channel")
    def on_mode(self, event):
        if event["channel"].get_setting("ban-enforce", False):
            bans = []
            kicks = set([])
            for mode, arg in event["modes"]:
                if mode[0] == "+" and mode[1] == "b":
                    bans.append(arg)

            if bans:
                umasks = {u.hostmask(): u for u in event["channel"].users}
                for ban in bans:
                    mask = utils.irc.hostmask_parse(ban)
                    matches = list(utils.irc.hostmask_match_many(
                        umasks.keys(), mask))
                    for match in matches:
                        kicks.add(umasks[match])
            if kicks:
                nicks = [u.nickname for u in kicks]
                event["channel"].send_kicks(sorted(nicks), REASON)
