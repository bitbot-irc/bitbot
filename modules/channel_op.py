import Utils

class Module(object):
    _name = "Channel Op"
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("command").on("kick", "k"
            ).hook(self.kick, channel_only=True, require_mode="o",
            min_args=1)

        bot.events.on("received").on("command").on("ban"
            ).hook(self.ban, channel_only=True, require_mode="o",
            min_args=1)
        bot.events.on("received").on("command").on("unban"
            ).hook(self.unban, channel_only=True, require_mode="o",
            min_args=1)

        bot.events.on("received").on("command").on("kickban", "kb"
            ).hook(self.kickban, channel_only=True, require_mode="o",
            min_args=1)

        bot.events.on("received").on("command").on("op"
            ).hook(self.op, channel_only=True, require_mode="o")
        bot.events.on("received").on("command").on("deop"
            ).hook(self.deop, channel_only=True, require_mode="o")

        bot.events.on("received").on("command").on("voice"
            ).hook(self.voice, channel_only=True, require_mode="o")
        bot.events.on("received").on("command").on("devoice"
            ).hook(self.devoice, channel_only=True, require_mode="o")

        bot.events.on("received").on("message").on("channel").hook(self.highlight_spam)

        bot.events.on("postboot").on("configure").on(
            "channelset").call(setting="highlight-spam-threshold",
            help="Set the number of nicknames in a message that qualifies as spam",
            validate=Utils.int_or_none)
        bot.events.on("postboot").on("configure").on(
            "channelset").call(setting="highlight-spam-protection",
            help="Enable/Disable highlight spam protection",
            validate=Utils.bool_or_none)
        bot.events.on("postboot").on("configure").on(
            "channelset").call(setting="highlight-spam-ban",
            help="Enable/Disable banning highlight spammers instead of just kicking",
            validate=Utils.bool_or_none)
        bot.events.on("postboot").on("configure").on(
            "channelset").call(setting="ban-format",
            help="Set ban format ($n = nick, $u = username, $h = hostname)")

    def kick(self, event):
        target = event["args_split"][0]
        target_user = event["server"].get_user(target)
        if event["args_split"][1:]:
            reason = " ".join(event["args_split"][1:])
        else:
            reason = None
        event["stderr"].set_prefix("Kick")
        if event["target"].has_user(target_user):
            if not event["server"].is_own_nickname(target):
                event["target"].send_kick(target, reason)
            else:
                event["stderr"].write("Nope.")
        else:
            event["stderr"].write("That user is not in this channel")

    def _ban_format(self, user, s):
        return s.replace("$n", user.nickname).replace("$u", user.username
            ).replace("$h", user.hostname)
    def _ban(self, channel, ban, user):
        format = channel.get_setting("ban-format", "*!$u@$h")
        hostmask_split = format.split("$$")
        hostmask_split = [self._ban_format(user, s) for s in hostmask_split]
        hostmask = "".join(hostmask_split)
        if ban:
            channel.send_ban(hostmask)
        else:
            channel.send_unban(hostmask)
    def ban(self, event):
        target_user = event["server"].get_user(event["args_split"][0])
        if event["target"].has_user(target_user):
            self._ban(event["target"], True, target_user)
        else:
            event["target"].send_ban(event["args_split"][0])
    def unban(self, event):
        target_user = event["server"].get_user(event["args_split"][0])
        if event["target"].has_user(target_user):
            self._ban(event["target"], False, target_user)
        else:
            event["target"].send_unban(event["args_split"][0])

    def kickban(self, event):
        if event["server"].has_user(event["args_split"][0]):
            self.ban(event)
            self.kick(event)
        else:
            event["stderr"].write("That user is not in this channel")

    def op(self, event):
        target = event["user"].nickname if not event["args_split"] else event[
            "args_split"][0]
        event["target"].send_mode("+o", target)
    def deop(self, event):
        target = event["user"].nickname if not event["args_split"] else event[
            "args_split"][0]
        event["target"].send_mode("-o", target)
    def voice(self, event):
        target = event["user"].nickname if not event["args_split"] else event[
            "args_split"][0]
        event["target"].send_mode("+v", target)
    def devoice(self, event):
        target = event["user"].nickname if not event["args_split"] else event[
            "args_split"][0]
        event["target"].send_mode("-v", target)

    def highlight_spam(self, event):
        if event["channel"].get_setting("highlight-spam-protection", False):
            nicknames = list(map(lambda user: user.nickname,
                event["channel"].users)) + [event["server"].nickname]

            if len(set(nicknames) & set(event["message_split"])
                    ) >= event["channel"].get_setting(
                    "highlight-spam-threshold", 10):
                has_mode = event["channel"].mode_or_above(event["user"], "v")
                should_ban = event["channel"].get_setting("highlight-spam-ban",
                    False)
                if not has_mode:
                    if should_ban:
                        event["channel"].send_ban("*!%s@%s" % (
                            event["user"].username, event["user"].hostname))
                    event["channel"].send_kick(event["user"].nickname,
                        "highlight spam detected")
