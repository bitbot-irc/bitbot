#--depends-on config

from bitbot import ModuleManager, utils

@utils.export("channelset", utils.IntSetting("highlight-spam-threshold",
    "Set the number of nicknames in a message that qualifies as spam"))
@utils.export("channelset", utils.BoolSetting("highlight-spam-protection",
    "Enable/Disable highlight spam protection"))
@utils.export("channelset", utils.BoolSetting("highlight-spam-ban",
    "Enable/Disable banning highlight spammers instead of just kicking"))
class Module(ModuleManager.BaseModule):
    @utils.hook("received.message.channel")
    def highlight_spam(self, event):
        if event["channel"].get_setting("highlight-spam-protection", False):
            nicknames = list(map(lambda user: user.nickname,
                event["channel"].users))

            highlights = set(nicknames) & set(event["message_split"])
            if len(highlights) > 1 and len(highlights) >= event["channel"
                    ].get_setting("highlight-spam-threshold", 10):
                has_mode = event["channel"].mode_or_above(event["user"], "v")
                should_ban = event["channel"].get_setting("highlight-spam-ban",
                    False)
                if not has_mode:
                    if should_ban:
                        event["channel"].send_ban("*!%s@%s" % (
                            event["user"].username, event["user"].hostname))
                    event["channel"].send_kick(event["user"].nickname,
                        "highlight spam detected")

