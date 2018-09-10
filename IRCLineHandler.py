import re, threading
import Utils

RE_PREFIXES = re.compile(r"\bPREFIX=\((\w+)\)(\W+)(?:\b|$)")
RE_CHANMODES = re.compile(
    r"\bCHANMODES=(\w*),(\w*),(\w*),(\w*)(?:\b|$)")
RE_CHANTYPES = re.compile(r"\bCHANTYPES=(\W+)(?:\b|$)")
RE_MODES = re.compile(r"[-+]\w+")

CAPABILITIES = {"multi-prefix", "chghost", "invite-notify", "account-tag",
    "account-notify", "extended-join", "away-notify", "userhost-in-names",
    "draft/message-tags-0.2", "server-time", "cap-notify",
    "batch", "draft/labeled-response"}

class LineHandler(object):
    def __init__(self, bot, events):
        self.bot = bot
        self.events = events
        events.on("raw.PING").hook(self.ping)

        events.on("raw.001").hook(self.handle_001, default_event=True)
        events.on("raw.005").hook(self.handle_005)
        events.on("raw.311").hook(self.handle_311, default_event=True)
        events.on("raw.332").hook(self.handle_332)
        events.on("raw.333").hook(self.handle_333)
        events.on("raw.353").hook(self.handle_353, default_event=True)
        events.on("raw.366").hook(self.handle_366, default_event=True)
        events.on("raw.421").hook(self.handle_421, default_event=True)
        events.on("raw.352").hook(self.handle_352, default_event=True)
        events.on("raw.354").hook(self.handle_354, default_event=True)
        events.on("raw.324").hook(self.handle_324, default_event=True)
        events.on("raw.329").hook(self.handle_329, default_event=True)
        events.on("raw.433").hook(self.handle_433, default_event=True)
        events.on("raw.477").hook(self.handle_477, default_event=True)

        events.on("raw.JOIN").hook(self.join)
        events.on("raw.PART").hook(self.part)
        events.on("raw.QUIT").hook(self.quit)
        events.on("raw.NICK").hook(self.nick)
        events.on("raw.MODE").hook(self.mode)
        events.on("raw.KICK").hook(self.kick)
        events.on("raw.INVITE").hook(self.invite)
        events.on("raw.TOPIC").hook(self.topic)
        events.on("raw.PRIVMSG").hook(self.privmsg)
        events.on("raw.NOTICE").hook(self.notice)

        events.on("raw.CAP").hook(self.cap)
        events.on("raw.AUTHENTICATE").hook(self.authenticate)
        events.on("raw.CHGHOST").hook(self.chghost)
        events.on("raw.ACCOUNT").hook(self.account)
        events.on("raw.TAGMSG").hook(self.tagmsg)
        events.on("raw.AWAY").hook(self.away)
        events.on("raw.BATCH").hook(self.batch)

    def handle(self, server, line):
        original_line = line
        tags = {}
        prefix = None
        command = None

        if line[0] == "@":
            tags_prefix, line = line[1:].split(" ", 1)
            for tag in tags_prefix.split(";"):
                if tag:
                    tag_split = tag.split("=", 1)
                    tags[tag_split[0]] = "".join(tag_split[1:])
        if "batch" in tags and tags["batch"] in server.batches:
            server.batches[tag["batch"]].append(line)
            return

        arbitrary = None
        if " :" in line:
            line, arbitrary = line.split(" :", 1)
            if line.endswith(" "):
                line = line[:-1]
        if line[0] == ":":
            prefix, command = line[1:].split(" ", 1)
            if " " in command:
                command, line = command.split(" ", 1)
        else:
            command = line
            if " " in line:
                command, line = line.split(" ", 1)
        args = line.split(" ")

        hooks = self.events.on("raw").on(command).get_hooks()
        default_event = False
        for hook in hooks:
            if hook.kwargs.get("default_event", False):
                default_event = True
                break
        last = arbitrary or args[-1]

        #server, prefix, command, args, arbitrary
        self.events.on("raw").on(command).call(server=server, last=last,
            prefix=prefix, args=args, arbitrary=arbitrary, tags=tags)
        if default_event or not hooks:
            if command.isdigit():
                self.events.on("received.numeric").on(command).call(
                    line=original_line, server=server, tags=tags, last=last,
                    line_split=original_line.split(" "), number=command)
            else:
                self.events.on("received").on(command).call(
                    line=original_line, line_split=original_line.split(" "),
                    command=command, server=server, tags=tags, last=last)

    # ping from the server
    def ping(self, event):
        event["server"].send_pong(event["last"])

    # first numeric line the server sends
    def handle_001(self, event):
        event["server"].name = Utils.remove_colon(event["prefix"])
        event["server"].set_own_nickname(event["args"][0])
        event["server"].send_whois(event["server"].nickname)

    # server telling us what it supports
    def handle_005(self, event):
        isupport_line = " ".join(event["args"][1:])

        if "NAMESX" in isupport_line:
            event["server"].send("PROTOCTL NAMESX")

        match = re.search(RE_PREFIXES, isupport_line)
        if match:
            event["server"].mode_prefixes.clear()
            modes = match.group(1)
            prefixes = match.group(2)
            for i, prefix in enumerate(prefixes):
                if i < len(modes):
                    event["server"].mode_prefixes[prefix] = modes[i]
        match = re.search(RE_CHANMODES, isupport_line)
        if match:
            event["server"].channel_modes = list(match.group(4))
        match = re.search(RE_CHANTYPES, isupport_line)
        if match:
            event["server"].channel_types = list(match.group(1))
        self.events.on("received.numeric.005").call(
            isupport=isupport_line, server=event["server"])

    # whois respose (nickname, username, realname, hostname)
    def handle_311(self, event):
        nickname = event["args"][1]
        if event["server"].is_own_nickname(nickname):
            target = event["server"]
        else:
            target = event["server"].get_user(nickname)
        target.username = event["args"][2]
        target.hostname = event["args"][3]
        target.realname = event["arbitrary"]

    # on-join channel topic line
    def handle_332(self, event):
        channel = event["server"].get_channel(event["args"][1])

        channel.set_topic(event["arbitrary"])
        self.events.on("received.numeric.332").call(channel=channel,
            server=event["server"], topic=event["arbitrary"])

    # channel topic changed
    def topic(self, event):
        nickname, username, hostname = Utils.seperate_hostmask(
            event["prefix"])
        user = event["server"].get_user(nickname)
        channel = event["server"].get_channel(event["args"][0])

        channel.set_topic(event["arbitrary"])
        self.events.on("received.topic").call(channel=channel,
            server=event["server"], topic=event["arbitrary"], user=user)

    # on-join channel topic set by/at
    def handle_333(self, event):
        channel = event["server"].get_channel(event["args"][1])

        topic_setter_hostmask = event["args"][2]
        nickname, username, hostname = Utils.seperate_hostmask(
            topic_setter_hostmask)
        topic_time = int(event["args"][3]) if event["args"][3].isdigit(
            ) else None

        channel.set_topic_setter(nickname, username, hostname)
        channel.set_topic_time(topic_time)
        self.events.on("received.numeric.333").call(channel=channel,
            setter=nickname, set_at=topic_time, server=event["server"])

    # /names response, also on-join user list
    def handle_353(self, event):
        channel = event["server"].get_channel(event["args"][2])
        nicknames = event["arbitrary"].split()
        for nickname in nicknames:
            modes = set([])

            while nickname[0] in event["server"].mode_prefixes:
                modes.add(event["server"].mode_prefixes[nickname[0]])
                nickname = nickname[1:]

            if "userhost-in-names" in event["server"].capabilities:
                nickname, username, hostname = Utils.seperate_hostmask(
                    nickname)
                user = event["server"].get_user(nickname)
                user.username = username
                user.hostname = hostname
            else:
                user = event["server"].get_user(nickname)
            user.join_channel(channel)
            channel.add_user(user)

            for mode in modes:
                channel.add_mode(mode, nickname)

    # on-join user list has finished
    def handle_366(self, event):
        event["server"].send_whox(event["args"][1], "ahnrtu", "001")

    # on user joining channel
    def join(self, event):
        nickname, username, hostname = Utils.seperate_hostmask(
            event["prefix"])
        account = None
        realname = None
        if len(event["args"]) == 2:
            channel = event["server"].get_channel(event["args"][0])
            if not event["args"] == "*":
                account = event["args"][1]
            realname = event["arbitrary"]
        else:
            channel = event["server"].get_channel(event["last"])

        if not event["server"].is_own_nickname(nickname):
            user = event["server"].get_user(nickname)
            if not event["server"].has_user(nickname):
                user.username = username
                user.hostname = hostname

            if account:
                user.identified_account = account
                user.identified_account_id = event["server"].get_user(
                    account).get_id()
            if realname:
                user.realname = realname

            channel.add_user(user)
            user.join_channel(channel)
            self.events.on("received.join").call(channel=channel,
                user=user, server=event["server"], account=account,
                realname=realname)
        else:
            if channel.name in event["server"].attempted_join:
                del event["server"].attempted_join[channel.name]
            self.events.on("self.join").call(channel=channel,
                server=event["server"], account=account, realname=realname)
            channel.send_mode()

    # on user parting channel
    def part(self, event):
        nickname, username, hostname = Utils.seperate_hostmask(
            event["prefix"])
        channel = event["server"].get_channel(event["args"][0])
        reason = event["arbitrary"] or ""

        if not event["server"].is_own_nickname(nickname):
            user = event["server"].get_user(nickname)
            self.events.on("received.part").call(channel=channel,
                reason=reason, user=user, server=event["server"])
            channel.remove_user(user)
            user.part_channel(channel)
            if not len(user.channels):
                event["server"].remove_user(user)
        else:
            event["server"].remove_channel(channel)
            self.events.on("self.part").call(channel=channel,
                reason=reason, server=event["server"])

    # unknown command sent by us, oops!
    def handle_421(self, event):
        print("warning: unknown command '%s'." % event["args"][1])

    # a user has disconnected!
    def quit(self, event):
        nickname, username, hostname = Utils.seperate_hostmask(
            event["prefix"])
        reason = event["arbitrary"] or ""

        if not event["server"].is_own_nickname(nickname):
            user = event["server"].get_user(nickname)
            event["server"].remove_user(user)
            self.events.on("received.quit").call(reason=reason,
                user=user, server=event["server"])
        else:
            event["server"].disconnect()

    # the server is telling us about its capabilities!
    def cap(self, event):
        capabilities_list = (event["arbitrary"] or "").split(" ")
        capabilities = {}
        for capability in capabilities_list:
            argument = None
            if "=" in capability:
                capability, argument = capability.split("=", 1)
            capabilities[capability] = argument

        subcommand = event["args"][1].lower()
        is_multiline = len(event["args"]) > 2 and event["args"][2] == "*"

        if subcommand == "ls":
            event["server"].server_capabilities.update(capabilities)
            if not is_multiline:
                matched_capabilities = set(event["server"
                    ].server_capabilities.keys()) & CAPABILITIES
                if matched_capabilities:
                    event["server"].queue_capabilities(matched_capabilities)

                    self.events.on("received.cap.ls").call(
                        capabilities=event["server"].server_capabilities,
                        server=event["server"])

                    if event["server"].has_capability_queue():
                        event["server"].send_capability_queue()
                    else:
                        event["server"].send_capability_end()
        elif subcommand == "new":
            event["server"].capabilities.update(set(capabilities.keys()))
            self.events.on("received.cap.new").call(server=event["server"],
                capabilities=capabilities)
        elif subcommand == "del":
            event["server"].capabilities.difference_update(set(
                capabilities.keys()))
            self.events.on("received.cap.del").call(server=event["server"],
                capabilities=capabilities)
        elif subcommand == "ack":
            event["server"].capabilities.update(capabilities)
            if not is_multiline:
                self.events.on("received.cap.ack").call(
                   capabilities=event["server"].capabilities,
                   server=event["server"])

                if not event["server"].waiting_for_capabilities():
                    event["server"].send_capability_end()
        elif subcommand == "nack":
            event["server"].send_capability_end()

    # the server is asking for authentication
    def authenticate(self, event):
        self.events.on("received.authenticate").call(
            message=event["args"][0], server=event["server"])

    # someone has changed their nickname
    def nick(self, event):
        nickname, username, hostname = Utils.seperate_hostmask(
            event["prefix"])
        new_nickname = event["arbitrary"]
        if not event["server"].is_own_nickname(nickname):
            user = event["server"].get_user(nickname)
            old_nickname = user.nickname
            user.set_nickname(new_nickname)
            event["server"].change_user_nickname(old_nickname, new_nickname)

            self.events.on("received.nick").call(new_nickname=new_nickname,
                old_nickname=old_nickname, user=user, server=event["server"])
        else:
            old_nickname = event["server"].nickname
            event["server"].set_own_nickname(new_nickname)

            self.events.on("self.nick").call(server=event["server"],
                new_nickname=new_nickname, old_nickname=old_nickname)

    # something's mode has changed
    def mode(self, event):
        nickname, username, hostname = Utils.seperate_hostmask(
            event["prefix"])
        user = event["server"].get_user(nickname)
        target = event["args"][0]
        is_channel = target[0] in event["server"].channel_types
        if is_channel:
            channel = event["server"].get_channel(target)
            remove = False
            args  = event["args"][2:]
            _args = args[:]
            modes = RE_MODES.findall(event["args"][1])
            for chunk in modes:
                remove = chunk[0] == "-"
                for mode in chunk[1:]:
                    if mode in event["server"].channel_modes:
                        channel.change_mode(remove, mode)
                    elif mode in event["server"].mode_prefixes.values(
                            ) and len(args):
                        channel.change_mode(remove, mode, args.pop(0))
                    else:
                        args.pop(0)
            self.events.on("received.mode.channel").call(modes=modes,
                mode_args=_args, channel=channel, server=event["server"],
                user=user)
        elif event["server"].is_own_nickname(target):
            modes = RE_MODES.findall(event["last"])
            for chunk in modes:
                remove = chunk[0] == "-"
                for mode in chunk[1:]:
                    event["server"].change_own_mode(remove, mode)
            self.events.on("self.mode").call(modes=modes,
                server=event["server"])

    # someone (maybe me!) has been invited somewhere
    def invite(self, event):
        nickname, username, hostname = Utils.seperate_hostmask(
            event["prefix"])
        target_channel = event["last"]
        user = event["server"].get_user(nickname)
        target_user = event["server"].get_user(event["args"][0])
        self.events.on("received.invite").call(user=user,
            target_channel=target_channel, server=event["server"],
            target_user=target_user)

    # we've received a message
    def privmsg(self, event):
        nickname, username, hostname = Utils.seperate_hostmask(
            event["prefix"])
        user = event["server"].get_user(nickname)
        message = event["arbitrary"] or ""
        message_split = message.split(" ")
        target = event["args"][0]
        action = message.startswith("\x01ACTION ")
        if action:
            message = message.replace("\x01ACTION ", "", 1)
            if message.endswith("\x01"):
                message = message[:-1]

        kwargs = {"message": message, "message_split": message_split,
            "server": event["server"], "tags": event["tags"],
            "action": action}

        if target[0] in event["server"].channel_types:
            channel = event["server"].get_channel(event["args"][0])
            self.events.on("received.message.channel").call(
                user=user, channel=channel, **kwargs)
            channel.buffer.add_line(user.nickname, message, action)
        elif event["server"].is_own_nickname(target):
            self.events.on("received.message.private").call(
                user=user, **kwargs)
            user.buffer.add_line(user.nickname, message, action)

    # we've received a notice
    def notice(self, event):
        message = event["arbitrary"] or ""
        message_split = message.split(" ")
        target = event["args"][0]
        sender = Utils.remove_colon(event["prefix"] or "")

        if sender == event["server"].name or target == "*" or not event[
                "prefix"]:
            event["server"].name = Utils.remove_colon(event["prefix"])

            self.events.on("received.server-notice").call(
                message=message, message_split=message_split,
                server=event["server"])
        else:
            nickname, username, hostname = Utils.seperate_hostmask(sender)
            user = event["server"].get_user(nickname)

            if target[0] in event["server"].channel_types:
                channel = event["server"].get_channel(target)
                self.events.on("received.notice.channel").call(
                    message=message, message_split=message_split, user=user,
                    server=event["server"], channel=channel,
                    tags=event["tags"])
            elif event["server"].is_own_nickname(target):
                self.events.on("received.notice.private").call(
                    message=message, message_split=message_split, user=user,
                    server=event["server"], tags=event["tags"])

    # IRCv3 TAGMSG, used to send tags without any other information
    def tagmsg(self, event):
        nickname, username, hostname = Utils.seperate_hostmask(
            event["prefix"])
        user = event["channel"].get_user(nickname)
        target = event["args"][0]

        if target[0] in event["server"].channel_types:
            channel = event["server"].get_channel(target)
            self.events.on("received.tagmsg.channel").call(channel=channel,
                user=user, tags=event["tags"], server=event["server"])
        elif event["server"].is_own_nickname(target):
            self.events.on("received.tagmsg.private").call(
                user=user, tags=event["tags"], server=event["server"])

    # IRCv3 AWAY, used to notify us that a client we can see has changed /away
    def away(self, event):
        nickname, username, hostname = Utils.seperate_hostmask(
            event["prefix"])
        user = event["server"].get_user(nickname)
        message = event["arbitrary"]
        if message:
            user.away = True
            self.events.on("received.away.on").call(user=user,
                server=event["server"], message=message)
        else:
            user.away = False
            self.events.on("received.away.off").call(user=user,
                server=event["server"])

    def batch(self, event):
        identifier = event["args"][0]
        modifier, identifier = identifier[0], identifier[1:]
        if modifier == "+":
            event["server"].batches[identifier] = []
        else:
            lines = event["server"].batches[identifier]
            del event["server"].batches[identifier]
            for line in lines:
                self.handle(event["server"], line)

    # IRCv3 CHGHOST, a user's username and/or hostname has changed
    def chghost(self, event):
        nickname, username, hostname = Utils.seperate_hostmask(
            event["prefix"])
        user = event["server"].get_user("nickanme")
        username = event["args"][0]
        hostname = event["args"][1]
        user.username = username
        user.hostname = hostname

    def account(self, event):
        nickname, username, hostname = Utils.seperate_hostmask(
            event["prefix"])
        user = event["server"].get_user("nickname")

        if not event["args"][0] == "*":
            user.identified_account = event["args"][0]
            user.identified_account_id = event["server"].get_user(
                event["args"][0]).get_id()
            self.events.on("received.account.login").call(user=user,
                server=event["server"], account=event["args"][0])
        else:
            user.identified_account = None
            user.identified_account_id = None
            self.events.on("received.account.logout").call(user=user,
                server=event["server"])

    # response to a WHO command for user information
    def handle_352(self, event):
        user = event["server"].get_user(event["args"][5])
        user.username = event["args"][2]
        user.hostname = event["args"][3]
    # response to a WHOX command for user information, including account name
    def handle_354(self, event):
        if event["args"][1] == "001":
            username = event["args"][2]
            hostname = event["args"][3]
            nickname = event["args"][4]
            account = event["args"][5]
            realname = event["last"]

            user = event["server"].get_user(nickname)
            user.username = username
            user.hostname = hostname
            user.realname = realname
            if not account == "0":
                user.identified_account = account

    # response to an empty mode command
    def handle_324(self, event):
        channel = event["server"].get_channel(event["args"][1])
        modes = event["args"][2]
        if modes[0] == "+" and modes[1:]:
            for mode in modes[1:]:
                if mode in event["server"].channel_modes:
                    channel.add_mode(mode)

    # channel creation unix timestamp
    def handle_329(self, event):
        channel = event["server"].get_channel(event["args"][1])
        channel.creation_timestamp = int(event["args"][2])

    # nickname already in use
    def handle_433(self, event):
        pass

    # we need a registered nickname for this channel
    def handle_477(self, event):
        if event["args"][1].lower() in event["server"].attempted_join:
            self.bot.add_timer("rejoin", 5,
                channel_name=event["args"][1],
                key=event["server"].attempted_join[event["args"][1].lower()],
                server_id=event["server"].id)

    # someone's been kicked from a channel
    def kick(self, event):
        nickname, username, hostname = Utils.seperate_hostmask(
            event["prefix"])
        user = event["server"].get_user(nickname)
        target = event["args"][1]
        channel = event["server"].get_channel(event["args"][0])
        reason = event["arbitrary"] or ""

        if not event["server"].is_own_nickname(target):
            target_user = event["server"].get_user(target)
            self.events.on("received.kick").call(channel=channel,
                reason=reason, target_user=target_user, user=user,
                server=event["server"])
        else:
            self.events.on("self.kick").call(channel=channel,
                reason=reason, user=user, server=event["server"])
