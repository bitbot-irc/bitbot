#--depends-on config

from src import ModuleManager, utils
import time

SETTING = utils.BoolSetting("accept-invites",
    "Set whether I accept invites")

SETTING2 = utils.BoolSetting("check-for-invite-op", "Whether I accept invites from non-chanops")    

THROTTLESECS = utils.IntSetting("invite-ratelimit-time", "Amount of time to wait in between invites")

badchans = []
tocheck = []

@utils.export("botset", SETTING)
@utils.export("serverset", SETTING)
@utils.export("serverset", SETTING2)
@utils.export("serverset", THROTTLESECS)
class Module(ModuleManager.BaseModule):
    def chanisbad(self, server, chan):
        now = time.time()
        for s, c, t in badchans:
            if (s, c) == (server, chan) and (now - t) < server.get_setting("invite-ratelimit-time", 60):
                return True
        return False

    @utils.hook("received.invite")
    def on_invite(self, event):
        if event["server"].is_own_nickname(event["target_user"].nickname):
            if event["server"].get_setting("accept-invites",
                    self.bot.get_setting("accept-invites", False)):
                if self.chanisbad(event["server"], event["target_channel"]):
                    event["server"].send_raw("NOTICE %s :Please wait a little while before inviting me again." % event["user"])
                    return
                tocheck.append((event["target_channel"], event["server"], event["user"]))
                event["server"].send_join(event["target_channel"])
                        
    @utils.hook("received.366")
    def on_names(self, event):
        chan = event["line"].args[1]
        if chan in [c for c, s, n in tocheck if event["server"] == s] and event["server"].get_setting("check-for-invite-op", False):
            n = [n for c, s, n in tocheck if (c, s) == (chan, event["server"])][0]
            if not event["server"].channels.get(chan).mode_or_above(n, "o"):
                event["server"].send_part(chan)
                event["server"].send_raw("NOTICE %s :You must be a channel operator (+o or higher) to invite me to %s" % (n, chan))
                badchans.append((event["server"], chan, time.time()))
