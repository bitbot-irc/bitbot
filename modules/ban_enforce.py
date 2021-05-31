from src import ModuleManager, utils

REASON = "User is banned from this channel"

@utils.export("channelset", utils.BoolSetting("ban-enforce",
    "Whether or not to parse new bans and kick who they affect"))
@utils.export("channelset", utils.IntSetting("ban-enforce-max",
    "Do not enforce ban if the ban effects more than this many users. Default is half of total channel users."))
class Module(ModuleManager.BaseModule):
    @utils.hook("received.mode.channel")
    def on_mode(self, event):
        if event["channel"].get_setting("ban-enforce", False):
            bans = []
            kicks = set([])
            for mode, arg in event["modes"]:
                if mode[0] == "+" and mode[1] == "b":
                    bans.append(arg)

            affected = 0
            defaultmax = len(event["channel"].users) // 2
            realmax = event["channel"].get_setting("ban-enforce-max", defaultmax)
            
            if bans:
                umasks = {u.hostmask(): u for u in event["channel"].users}
                for ban in bans:
                    mask = utils.irc.hostmask_parse(ban)
                    matches = list(utils.irc.hostmask_match_many(
                        umasks.keys(), mask))
                    for match in matches:
                        affected = affected + 1
                        kicks.add(umasks[match])
            if kicks:
                if affected > realmax:
                    return
                nicks = [u.nickname for u in kicks]
                event["channel"].send_kicks(sorted(nicks), REASON)
