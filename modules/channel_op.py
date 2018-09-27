from src import ModuleManager, Utils

@Utils.export("channelset", {"setting": "highlight-spam-threshold",
    "help": "Set the number of nicknames in a message that qualifies as spam",
     "validate": Utils.int_or_none})
@Utils.export("channelset", {"setting": "highlight-spam-protection",
    "help": "Enable/Disable highlight spam protection",
    "validate": Utils.bool_or_none})
@Utils.export("channelset", {"setting": "highlight-spam-ban",
    "help": "Enable/Disable banning highlight spammers "
    "instead of just kicking", "validate": Utils.bool_or_none})
@Utils.export("channelset", {"setting": "ban-format",
    "help": "Set ban format ($n = nick, $u = username, $h = hostname)"})
class Module(ModuleManager.BaseModule):
    _name = "Channel Op"

    @Utils.hook("received.command.kick|k", channel_only=True,
        require_mode="o", usage="<nickname> [reason]", min_args=1)
    def kick(self, event):
        """
        Kick a user from the current channel
        """
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

    @Utils.hook("received.command.ban", channel_only=True, min_args=1,
        require_mode="o", usage="<nickname/hostmask>")
    def ban(self, event):
        """
        Ban a user/hostmask from the current channel
        """
        target_user = event["server"].get_user(event["args_split"][0])
        if event["target"].has_user(target_user):
            self._ban(event["target"], True, target_user)
        else:
            event["target"].send_ban(event["args_split"][0])
    @Utils.hook("received.command.unban", channel_only=True, min_args=1,
        require_mode="o", usage="<nickname/hostmask>")
    def unban(self, event):
        """
        Unban a user/hostmask from the current channel
        """
        target_user = event["server"].get_user(event["args_split"][0])
        if event["target"].has_user(target_user):
            self._ban(event["target"], False, target_user)
        else:
            event["target"].send_unban(event["args_split"][0])

    @Utils.hook("received.command.kickban|kb", channel_only=True,
        require_mode="o", usage="<nickname> [reason]", min_args=1)
    def kickban(self, event):
        """
        Kick and ban a user from the current channel
        """
        if event["server"].has_user(event["args_split"][0]):
            self.ban(event)
            self.kick(event)
        else:
            event["stderr"].write("That user is not in this channel")

    @Utils.hook("received.command.op", channel_only=True,
        require_mode="o", usage="[nickname]")
    def op(self, event):
        """
        Op a user in the current channel
        """
        target = event["user"].nickname if not event["args_split"] else event[
            "args_split"][0]
        event["target"].send_mode("+o", target)
    @Utils.hook("received.command.deop", channel_only=True,
        require_mode="o", usage="[nickname]")
    def deop(self, event):
        """
        Remove op from a user in the current channel
        """
        target = event["user"].nickname if not event["args_split"] else event[
            "args_split"][0]
        event["target"].send_mode("-o", target)

    @Utils.hook("received.command.voice", channel_only=True,
        require_mode="o", usage="[nickname]")
    def voice(self, event):
        """
        Voice a user in the current channel
        """
        target = event["user"].nickname if not event["args_split"] else event[
            "args_split"][0]
        event["target"].send_mode("+v", target)
    @Utils.hook("received.command.devoice", channel_only=True,
        require_mode="o", usage="[nickname]")
    def devoice(self, event):
        """
        Remove voice from a user in the current channel
        """
        target = event["user"].nickname if not event["args_split"] else event[
            "args_split"][0]
        event["target"].send_mode("-v", target)

    @Utils.hook("received.command.topic", min_args=1, require_mode="o",
        channel_only=True, usage="<topic>")
    def topic(self, event):
        """
        Set the topic in the current channel
        """
        event["target"].send_topic(event["args"])
    @Utils.hook("received.command.tappend", min_args=1, require_mode="o",
        channel_only=True, usage="<topic>")
    def tappend(self, event):
        """
        Append to the topic in the current channel
        """
        event["target"].send_topic(event["target"].topic + event["args"])

    @Utils.hook("received.message.channel")
    def highlight_spam(self, event):
        if event["channel"].get_setting("highlight-spam-protection", False):
            nicknames = list(map(lambda user: user.nickname,
                event["channel"].users)) + [event["server"].nickname]

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
