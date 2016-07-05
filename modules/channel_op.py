

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

    def ban(self, event):
        target_user = event["server"].get_user(event["args_split"][0])
        if event["target"].has_user(target_user):
            event["target"].send_ban("*!%s@%s" % (target_user.username,
                target_user.hostname))
        else:
            event["target"].send_ban(event["args_split"][0])

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
