from src import ModuleManager, utils

class UserNotFoundException(Exception):
    pass
class InvalidTimeoutException(Exception):
    pass

@utils.export("channelset", {"setting": "highlight-spam-threshold",
    "help": "Set the number of nicknames in a message that qualifies as spam",
     "validate": utils.int_or_none})
@utils.export("channelset", {"setting": "highlight-spam-protection",
    "help": "Enable/Disable highlight spam protection",
    "validate": utils.bool_or_none})
@utils.export("channelset", {"setting": "highlight-spam-ban",
    "help": "Enable/Disable banning highlight spammers "
    "instead of just kicking", "validate": utils.bool_or_none})
@utils.export("channelset", {"setting": "ban-format",
    "help": "Set ban format ($n = nick, $u = username, $h = hostname)"})
class Module(ModuleManager.BaseModule):
    _name = "Channel Op"

    @utils.hook("timer.unban")
    def _timer_unban(self, event):
        server = self.bot.get_server(event["server_id"])
        if event["channel_name"] in server.channels:
            channel = server.channels.get(event["channel_name"])
            channel.send_unban(event["hostmask"])

    def _kick(self, server, channel, nickname, reason):
        target_user = server.get_user(nickname)
        if channel.has_user(target_user):
            channel.send_kick(nickname, reason)
        else:
            raise UserNotFoundException("That user is not in this channel")
    def _kick_command(self, event, channel, args_split):
        target = args_split[0]
        reason = " ".join(args_split[1:]) or None

        try:
            self._kick(event["server"], event["target"], target, reason)
        except UserNotFoundException:
            event["stderr"].write(str(e))

    @utils.hook("received.command.kick", private_only=True, min_args=2)
    def private_kick(self, event):
        """
        :help: Kick a user from the current channel
        :usage: <nickname> [reason]
        :require_access: kick
        :channel_arg: 0
        :prefix: Kick
        """
        channel = event["server"].channels.get(event["args_split"][0])
        self._kick_command(event, channel, event["args_split"][1:])

    @utils.hook("received.command.k", alias_of="kick")
    @utils.hook("received.command.kick", channel_only=True, min_args=1)
    def kick(self, event):
        """
        :help: Kick a user from the current channel
        :usage: <nickname> [reason]
        :require_mode: o
        :require_access: kick
        :prefix: Kick
        """
        self._kick_command(event, event["target"], event["args_split"])

    def _ban_format(self, user, s):
        return s.replace("$n", user.nickname).replace("$u", user.username
            ).replace("$h", user.hostname)
    def _ban_user(self, channel, ban, user):
        if channel.has_user(user):
            format = channel.get_setting("ban-format", "*!$u@$h")
            hostmask_split = format.split("$$")
            hostmask_split = [self._ban_format(user, s) for s in hostmask_split]
            hostmask = "".join(hostmask_split)
            if ban:
                channel.send_ban(hostmask)
            else:
                channel.send_unban(hostmask)
            return hostmask
        else:
            raise UserNotFoundException("That user is not in this channel")

    def _ban(self, server, channel, ban, target):
        target_user = server.get_user(target)
        if channel.has_user(target_user):
            return self._ban_user(channel, ban, target_user)
        else:
            if ban:
                event["target"].send_ban(target)
            else:
                event["target"].send_unban(target)
            return target

    @utils.hook("received.command.ban", private_only=True, min_args=2)
    def private_ban(self, event):
        """
        :help: Ban a user/hostmask from the current channel
        :usage: <channel> <nickname/hostmask>
        :require_access: ban
        :channel_arg: 0
        """
        channel = event["server"].channels.get(event["args_split"][0])
        self._ban(event["server"], channel, True, event["args_split"][1])
    @utils.hook("received.command.ban", channel_only=True, min_args=1)
    def ban(self, event):
        """
        :help: Ban a user/hostmask from the current channel
        :usage: <nickname/hostmask>
        :require_mode: o
        :require_access: ban
        """
        self._ban(event["server"], event["target"], True,
            event["args_split"][0])

    def _temp_ban(self, event, accept_hostmask):
        timeout = utils.from_pretty_time(event["args_split"][1])
        if not timeout:
            raise InvalidTimeoutException(
                "Please provided a valid time above 0 seconds")

        if accept_hostmask:
            hostmask = self._ban(event["server"], event["target"], True,
                event["args_split"][0])
        else:
            hostmask = self._ban_user(event["target"], True,
                event["server"].get_user(event["args_split"][0]))

        self.timers.add_persistent("unban", timeout,
            server_id=event["server"].id,
            channel_name=event["target"].name, hostmask=hostmask)

    @utils.hook("received.command.tb", alias_of="tempban")
    @utils.hook("received.command.tempban", channel_only=True, min_args=2)
    def temp_ban(self, event):
        """
        :help: Temporarily ban someone from the current channel
        :usage: <nickname/hostmask> <time> [reason]
        :require_mode: o
        :require_access: ban
        :prefix: Tempban
        """
        try:
            self._temp_ban(event, True)
        except InvalidTimeoutException as e:
            event["stderr"].write(str(e))

    @utils.hook("received.command.tkb", alias_of="tempkickban")
    @utils.hook("received.command.tempkickban", channel_only=True,
        min_args=2)
    def temp_kick_ban(self, event):
        """
        :help: Temporarily kick and ban someone from the current channel
        :usage: <nickname> <time> [reason]
        :require_mode: o
        :require_access: kickban
        :prefix: TKB
        """
        reason = " ".join(event["args_split"][2:]) or None
        try:
            self._temp_ban(event, False)
            self._kick(event["server"], event["target"], event["args_split"][0],
                reason)
        except InvalidTimeoutException as e:
            event["stderr"].write(str(e))
        except UserNotFoundException as e:
            event["stderr"].write(str(e))

    @utils.hook("received.command.unban", channel_only=True, min_args=1)
    def unban(self, event):
        """
        :help: Unban a user/hostmask from the current channel
        :usage: <nickname/hostmask>
        :require_mode: o
        :require_access: ban
        """
        self._ban(event["server"], event["target"], False,
            event["args_split"][0])

    @utils.hook("received.command.kb", alias_of="kickban")
    @utils.hook("received.command.kickban", channel_only=True, min_args=1)
    def kickban(self, event):
        """
        :help: Kick and ban a user from the current channel
        :usage: <nickname> [reason]
        :require_mode: o
        :require_access: kickban
        :prefix: Kickban
        """
        target = event["args_split"][0]
        reason = " ".join(event["args_split"][1:]) or None
        try:
            self._ban(event["server"], event["target"], True, target)
            self._kick(event["server"], event["target"], target, reason)
        except UserNotFoundException as e:
            event["stderr"].write(str(e))

    @utils.hook("received.command.op", channel_only=True)
    def op(self, event):
        """
        :help: Op a user in the current channel
        :usage: [nickname]
        :require_mode: o
        :require_access: op
        """
        target = event["user"].nickname if not event["args_split"] else event[
            "args_split"][0]
        event["target"].send_mode("+o", target)
    @utils.hook("received.command.deop", channel_only=True)
    def deop(self, event):
        """
        :help: Remove op from a user in the current channel
        :usage: [nickname]
        :require_mode: o
        :require_access: op
        """
        target = event["user"].nickname if not event["args_split"] else event[
            "args_split"][0]
        event["target"].send_mode("-o", target)

    @utils.hook("received.command.voice", channel_only=True)
    def voice(self, event):
        """
        :help: Voice a user in the current channel
        :usage: [nickname]
        :require_mode: o
        :require_access: voice
        """
        target = event["user"].nickname if not event["args_split"] else event[
            "args_split"][0]
        event["target"].send_mode("+v", target)
    @utils.hook("received.command.devoice", channel_only=True)
    def devoice(self, event):
        """
        :help: Remove voice from a user in the current channel
        :usage: [nickname]
        :require_mode: o
        :require_access: voice
        """
        target = event["user"].nickname if not event["args_split"] else event[
            "args_split"][0]
        event["target"].send_mode("-v", target)

    @utils.hook("received.command.topic", min_args=1, channel_only=True,
        remove_empty=False)
    def topic(self, event):
        """
        :help: Set the topic in the current channel
        :usage: <topic>
        :require_mode: o
        :require_access: topic
        """
        event["target"].send_topic(event["args"])
    @utils.hook("received.command.tappend", min_args=1, channel_only=True,
        remove_empty=False)
    def tappend(self, event):
        """
        :help: Append to the topic in the current channel
        :usage: <topic>
        :require_mode: o
        :require_access: topic
        """
        event["target"].send_topic(event["target"].topic + event["args"])

    @utils.hook("received.message.channel")
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

    @utils.hook("received.command.leave", channel_only=True)
    def leave(self, event):
        """
        :help: Part me from the current channel
        :require_mode: o
        """
        event["target"].send_part()
