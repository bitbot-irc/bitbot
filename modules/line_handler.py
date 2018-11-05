import re, threading
from src import ModuleManager, utils

RE_PREFIXES = re.compile(r"\bPREFIX=\((\w+)\)(\W+)(?:\b|$)")
RE_CHANMODES = re.compile(
    r"\bCHANMODES=(\w*),(\w*),(\w*),(\w*)(?:\b|$)")
RE_CHANTYPES = re.compile(r"\bCHANTYPES=(\W+)(?:\b|$)")
RE_CASEMAPPING = re.compile(r"\bCASEMAPPING=(\S+)")
RE_MODES = re.compile(r"[-+]\w+")

CAPABILITIES = {"multi-prefix", "chghost", "invite-notify", "account-tag",
    "account-notify", "extended-join", "away-notify", "userhost-in-names",
    "draft/message-tags-0.2", "server-time", "cap-notify",
    "batch", "draft/labeled-response", "draft/rename"}

class Module(ModuleManager.BaseModule):
    def _handle(self, server, line):
        hooks = self.events.on("raw").on(line.command).get_hooks()
        default_events = []
        for hook in hooks:
            default_events.append(hook.kwargs.get("default_event", False))
        default_event = any(default_events)

        kwargs = {"args": line.args, "tags": line.tags, "server": server,
            "prefix": line.prefix}

        self.events.on("raw").on(line.command).call_unsafe(**kwargs)
        if default_event or not hooks:
            if line.command.isdigit():
                self.events.on("received.numeric").on(line.command).call(
                    **kwargs)
            else:
                self.events.on("received").on(line.command).call(**kwargs)

    @utils.hook("raw")
    def handle_raw(self, event):
        line = utils.irc.parse_line(event["line"])
        if "batch" in line.tags and line.tags["batch"] in event[
                "server"].batches:
            server.batches[tag["batch"]].append(line)
        else:
            self._handle(event["server"], line)

    @utils.hook("preprocess.send")
    def handle_send(self, event):
        line = utils.irc.parse_line(event["line"])
        self.events.on("send").on(line.command).call(
            args=line.args, tags=line.tags, server=event["server"])

    # ping from the server
    @utils.hook("raw.ping")
    def ping(self, event):
        event["server"].send_pong(event["args"].get(0))

    # first numeric line the server sends
    @utils.hook("raw.001", default_event=True)
    def handle_001(self, event):
        event["server"].name = event["prefix"].nickname
        event["server"].set_own_nickname(event["args"][0])
        event["server"].send_whois(event["server"].nickname)

    # server telling us what it supports
    @utils.hook("raw.005")
    def handle_005(self, event):
        isupport_line = " ".join(event["args"][1:])

        if "NAMESX" in isupport_line:
            event["server"].send("PROTOCTL NAMESX")

        match = re.search(RE_PREFIXES, isupport_line)
        if match:
            event["server"].prefix_symbols.clear()
            event["server"].prefix_modes.clear()
            modes = match.group(1)
            symbols = match.group(2)
            for symbol, mode in zip(symbols, modes):
                event["server"].prefix_symbols[symbol] = mode
                event["server"].prefix_modes[mode] = symbol
        match = re.search(RE_CHANMODES, isupport_line)
        if match:
            event["server"].channel_modes = list(match.group(4))
        match = re.search(RE_CHANTYPES, isupport_line)
        if match:
            event["server"].channel_types = list(match.group(1))

        match = re.search(RE_CASEMAPPING, isupport_line)
        if match:
            event["server"].case_mapping = match.group(1)

        self.events.on("received.numeric.005").call(
            isupport=isupport_line, server=event["server"])

    # whois respose (nickname, username, realname, hostname)
    @utils.hook("raw.311", default_event=True)
    def handle_311(self, event):
        nickname = event["args"][1]
        if event["server"].is_own_nickname(nickname):
            target = event["server"]
        else:
            target = event["server"].get_user(nickname)
        target.username = event["args"][2]
        target.hostname = event["args"][3]
        target.realname = event["args"][4]

    # on-join channel topic line
    @utils.hook("raw.332")
    def handle_332(self, event):
        channel = event["server"].get_channel(event["args"][1])
        topic = event["args"].get(2)
        channel.set_topic(topic)
        self.events.on("received.numeric.332").call(channel=channel,
            server=event["server"], topic=topic)

    # channel topic changed
    @utils.hook("raw.topic")
    def topic(self, event):
        user = event["server"].get_user(event["prefix"].nickname)
        channel = event["server"].get_channel(event["args"][0])
        topic = event["args"].get(1)
        channel.set_topic(topic)
        self.events.on("received.topic").call(channel=channel,
            server=event["server"], topic=topic, user=user)

    # on-join channel topic set by/at
    @utils.hook("raw.333")
    def handle_333(self, event):
        channel = event["server"].get_channel(event["args"][1])

        topic_setter_hostmask = event["args"][2]
        topic_setter = utils.irc.seperate_hostmask(topic_setter_hostmask)
        topic_time = int(event["args"][3]) if event["args"][3].isdigit(
            ) else None

        channel.set_topic_setter(topic_setter.nickname, topic_setter.username,
            topic_setter.hostname)
        channel.set_topic_time(topic_time)
        self.events.on("received.numeric.333").call(channel=channel,
            setter=topic_setter.nickname, set_at=topic_time,
            server=event["server"])

    # /names response, also on-join user list
    @utils.hook("raw.353", default_event=True)
    def handle_353(self, event):
        channel = event["server"].get_channel(event["args"][2])
        nicknames = event["args"].get(3).split()
        for nickname in nicknames:
            modes = set([])

            while nickname[0] in event["server"].prefix_symbols:
                modes.add(event["server"].prefix_symbols[nickname[0]])
                nickname = nickname[1:]

            if "userhost-in-names" in event["server"].capabilities:
                hostmask = utils.irc.seperate_hostmask(nickname)
                nickname = hostmask.nickname
                user = event["server"].get_user(hostmask.nickname)
                user.username = hostmask.username
                user.hostname = hostmask.hostname
            else:
                user = event["server"].get_user(nickname)
            user.join_channel(channel)
            channel.add_user(user)

            for mode in modes:
                channel.add_mode(mode, nickname)

    # on-join user list has finished
    @utils.hook("raw.366", default_event=True)
    def handle_366(self, event):
        event["server"].send_whox(event["args"][1], "n", "ahnrtu", "111")

    # on user joining channel
    @utils.hook("raw.join")
    def join(self, event):
        account = None
        realname = None
        if len(event["args"]) == 2:
            channel = event["server"].get_channel(event["args"][0])
            if not event["args"][1] == "*":
                account = event["args"][1]
            realname = event["args"][2]
        else:
            channel = event["server"].get_channel(event["args"][0])

        if not event["server"].is_own_nickname(event["prefix"].nickname):
            user = event["server"].get_user(event["prefix"].nickname)
            if not user.username and not user.hostname:
                user.username = event["prefix"].username
                user.hostname = event["prefix"].hostname

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
    @utils.hook("raw.part")
    def part(self, event):
        channel = event["server"].get_channel(event["args"][0])
        reason = event["args"].get(1)

        if not event["server"].is_own_nickname(event["prefix"].nickname):
            user = event["server"].get_user(event["prefix"].nickname)
            self.events.on("received.part").call(channel=channel,
                reason=reason, user=user, server=event["server"])
            channel.remove_user(user)
            user.part_channel(channel)
            if not len(user.channels):
                event["server"].remove_user(user)
        else:
            self.events.on("self.part").call(channel=channel,
                reason=reason, server=event["server"])
            event["server"].remove_channel(channel)

    # unknown command sent by us, oops!
    @utils.hook("raw.421", default_event=True)
    def handle_421(self, event):
        print("warning: unknown command '%s'." % event["args"][1])

    # a user has disconnected!
    @utils.hook("raw.quit")
    def quit(self, event):
        reason = event["args"].get(0)

        if not event["server"].is_own_nickname(event["prefix"].nickname):
            user = event["server"].get_user(event["prefix"].nickname)
            event["server"].remove_user(user)
            self.events.on("received.quit").call(reason=reason,
                user=user, server=event["server"])
        else:
            event["server"].disconnect()

    # the server is telling us about its capabilities!
    @utils.hook("raw.cap")
    def cap(self, event):
        capabilities_list = event["args"][2].split(" ")
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
    @utils.hook("raw.authenticate")
    def authenticate(self, event):
        self.events.on("received.authenticate").call(
            message=event["args"][0], server=event["server"])

    # someone has changed their nickname
    @utils.hook("raw.nick")
    def nick(self, event):
        new_nickname = event["args"].get(0)
        if not event["server"].is_own_nickname(event["prefix"].nickname):
            user = event["server"].get_user(event["prefix"].nickname)
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
    @utils.hook("raw.mode")
    def mode(self, event):
        user = event["server"].get_user(event["prefix"].nickname)
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
                    elif mode in event["server"].prefix_modes and len(args):
                        channel.change_mode(remove, mode, args.pop(0))
                    else:
                        args.pop(0)
            self.events.on("received.mode.channel").call(modes=modes,
                mode_args=_args, channel=channel, server=event["server"],
                user=user)
        elif event["server"].is_own_nickname(target):
            modes = RE_MODES.findall(event["args"][1])
            for chunk in modes:
                remove = chunk[0] == "-"
                for mode in chunk[1:]:
                    event["server"].change_own_mode(remove, mode)
            self.events.on("self.mode").call(modes=modes,
                server=event["server"])

    # someone (maybe me!) has been invited somewhere
    @utils.hook("raw.invite")
    def invite(self, event):
        target_channel = event["args"][0]
        user = event["server"].get_user(event["prefix"].nickname)
        target_user = event["server"].get_user(event["args"][0])
        self.events.on("received.invite").call(user=user,
            target_channel=target_channel, server=event["server"],
            target_user=target_user)

    # we've received a message
    @utils.hook("raw.privmsg")
    def privmsg(self, event):
        user = event["server"].get_user(event["prefix"].nickname)
        message = event["args"][1]
        message_split = message.split(" ")
        target = event["args"][0]
        action = message.startswith("\x01ACTION ")
        if action:
            message = message.replace("\x01ACTION ", "", 1)
            if message.endswith("\x01"):
                message = message[:-1]

        if "account" in event["tags"]:
            user.identified_account = event["tags"]["account"]
            user.identified_account_id = event["server"].get_user(
                event["tags"]["account"]).get_id()

        kwargs = {"message": message, "message_split": message_split,
            "server": event["server"], "tags": event["tags"],
            "action": action}

        if target[0] in event["server"].channel_types:
            channel = event["server"].get_channel(event["args"][0])
            self.events.on("received.message.channel").call(
                user=user, channel=channel, **kwargs)
            channel.buffer.add_message(user.nickname, message, action,
                event["tags"])
        elif event["server"].is_own_nickname(target):
            self.events.on("received.message.private").call(
                user=user, **kwargs)
            user.buffer.add_message(user.nickname, message, action,
                event["tags"])

    # we've received a notice
    @utils.hook("raw.notice")
    def notice(self, event):
        message = event["args"][1]
        message_split = message.split(" ")
        target = event["args"][0]

        if not event["prefix"] or event["prefix"].hostmask == event["server"
                ].name or target == "*" or (not event["prefix"].hostname and
                not event["server"].name):
            event["server"].name = event["prefix"].hostmask

            self.events.on("received.server-notice").call(
                message=message, message_split=message_split,
                server=event["server"])
        else:
            user = event["server"].get_user(event["prefix"].nickname)

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
    @utils.hook("raw.tagmsg")
    def tagmsg(self, event):
        user = event["server"].get_user(event["prefix"].nickname)
        target = event["args"][0]

        if target[0] in event["server"].channel_types:
            channel = event["server"].get_channel(target)
            self.events.on("received.tagmsg.channel").call(channel=channel,
                user=user, tags=event["tags"], server=event["server"])
        elif event["server"].is_own_nickname(target):
            self.events.on("received.tagmsg.private").call(
                user=user, tags=event["tags"], server=event["server"])

    # IRCv3 AWAY, used to notify us that a client we can see has changed /away
    @utils.hook("raw.away")
    def away(self, event):
        user = event["server"].get_user(event["prefix"].nickname)
        message = event["args"].get(0)
        if message:
            user.away = True
            self.events.on("received.away.on").call(user=user,
                server=event["server"], message=message)
        else:
            user.away = False
            self.events.on("received.away.off").call(user=user,
                server=event["server"])

    @utils.hook("raw.batch")
    def batch(self, event):
        identifier = event["args"][0]
        modifier, identifier = identifier[0], identifier[1:]
        if modifier == "+":
            event["server"].batches[identifier] = []
        else:
            lines = event["server"].batches[identifier]
            del event["server"].batches[identifier]
            for line in lines:
                self._handle(line)

    # IRCv3 CHGHOST, a user's username and/or hostname has changed
    @utils.hook("raw.chghost")
    def chghost(self, event):
        username = event["args"][0]
        hostname = event["args"][1]

        if not event["server"].is_own_nickname(event["prefix"].nickname):
            target = event["server"].get_user("nickanme")
        else:
            target = event["server"]
        target.username = username
        target.hostname = hostname

    @utils.hook("raw.account")
    def account(self, event):
        user = event["server"].get_user(event["prefix"].nickname)

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
    @utils.hook("raw.352", default_event=True)
    def handle_352(self, event):
        user = event["server"].get_user(event["args"][5])
        user.username = event["args"][2]
        user.hostname = event["args"][3]
    # response to a WHOX command for user information, including account name
    @utils.hook("raw.354", default_event=True)
    def handle_354(self, event):
        if event["args"][1] == "111":
            username = event["args"][2]
            hostname = event["args"][3]
            nickname = event["args"][4]
            account = event["args"][5]
            realname = event["args"][6]

            user = event["server"].get_user(nickname)
            user.username = username
            user.hostname = hostname
            user.realname = realname
            if not account == "0":
                user.identified_account = account

    # response to an empty mode command
    @utils.hook("raw.324", default_event=True)
    def handle_324(self, event):
        channel = event["server"].get_channel(event["args"][1])
        modes = event["args"][2]
        if modes[0] == "+" and modes[1:]:
            for mode in modes[1:]:
                if mode in event["server"].channel_modes:
                    channel.add_mode(mode)

    # channel creation unix timestamp
    @utils.hook("raw.329", default_event=True)
    def handle_329(self, event):
        channel = event["server"].get_channel(event["args"][1])
        channel.creation_timestamp = int(event["args"][2])

    # nickname already in use
    @utils.hook("raw.433", default_event=True)
    def handle_433(self, event):
        pass

    # we need a registered nickname for this channel
    @utils.hook("raw.477", default_event=True)
    def handle_477(self, event):
        channel_name = utils.irc.lower(event["server"].case_mapping,
            event["args"][1])
        if channel_name in event["server"]:
            key = event["server"].attempted_join[channel_name]
            self.timers.add("rejoin", 5, channel_name=channe_name, key=key,
                server_id=event["server"].id)

    # someone's been kicked from a channel
    @utils.hook("raw.kick")
    def kick(self, event):
        user = event["server"].get_user(event["prefix"].nickname)
        target = event["args"][1]
        channel = event["server"].get_channel(event["args"][0])
        reason = event["args"].get(2)

        if not event["server"].is_own_nickname(target):
            target_user = event["server"].get_user(target)
            self.events.on("received.kick").call(channel=channel,
                reason=reason, target_user=target_user, user=user,
                server=event["server"])
        else:
            self.events.on("self.kick").call(channel=channel,
                reason=reason, user=user, server=event["server"])

    # a channel has been renamed
    @utils.hook("raw.rename")
    def rename(self, event):
        old_name = event["args"][0]
        new_name = event["args"][1]
        channel = event["server"].get_channel(old_name)

        event["server"].rename_channel(old_name, new_name)
        self.events.on("received.rename").call(channel=channel,
            old_name=old_name, new_name=new_name,
            reason=event["args"].get(2))
