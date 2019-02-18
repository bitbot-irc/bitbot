import codecs, enum, re, threading
from src import ModuleManager, utils

RE_ISUPPORT_ESCAPE = re.compile(r"\\x(\d\d)", re.I)
RE_MODES = re.compile(r"[-+]\w+")

CAPABILITIES = {"multi-prefix", "chghost", "invite-notify", "account-tag",
    "account-notify", "extended-join", "away-notify", "userhost-in-names",
    "draft/message-tags-0.2", "draft/message-tags-0.3", "server-time",
    "cap-notify", "batch", "draft/labeled-response", "draft/rename",
    "echo-message", "draft/setname"}

LABELED_BATCH = {
    "labeled-response": "label",
    "draft/labeled-response": "draft/label"
}

class Direction(enum.Enum):
    SEND = 0
    RECV = 1

class Module(ModuleManager.BaseModule):
    def _handle(self, server, line):
        hooks = self.events.on("raw.received").on(line.command).get_hooks()
        default_events = []
        for hook in hooks:
            default_events.append(hook.kwargs.get("default_event", False))
        default_event = any(default_events)

        kwargs = {"args": line.args, "tags": line.tags, "server": server,
            "prefix": line.prefix, "direction": Direction.RECV}

        self.events.on("raw.received").on(line.command).call_unsafe(**kwargs)
        if default_event or not hooks:
            self.events.on("received").on(line.command).call(**kwargs)

    @utils.hook("raw.received")
    def handle_raw(self, event):
        line = utils.irc.parse_line(event["line"])
        if "batch" in line.tags and line.tags["batch"] in event[
                "server"].batches:
            server.batches[tag["batch"]].lines.append(line)
        else:
            self._handle(event["server"], line)

    @utils.hook("raw.send")
    def handle_send(self, event):
        line = utils.irc.parse_line(event["line"])
        self.events.on("raw.send").on(line.command).call_unsafe(
            args=line.args, tags=line.tags, server=event["server"],
            direction=Direction.SEND)

    def _event(self, event, event_name: str, **kwargs: dict):
        direction = event["direction"]
        if direction == Direction.RECV:
            root_event = self.events.on("received")
        elif direction == Direction.SEND:
            root_event = self.events.on("send")
        root_event.on(event_name).call(**kwargs)

    # ping from the server
    @utils.hook("raw.received.ping")
    def ping(self, event):
        event["server"].send_pong(event["args"].get(0))

    @utils.hook("raw.received.error")
    def error(self, event):
        self.log.error("ERROR received: %s", [event["args"][0]])
    @utils.hook("raw.received.fail")
    def fail(self, event):
        command = event["args"][0]
        error_code = event["args"][1]
        context = event["args"][2:-1]
        description = event["args"][-1]

        self.log.warn("FAIL (%s %s) received: %s" %
            (command, error_code, description))
        self.events.on("received.fail").call(command=command,
            error_code=error_code, context=context, description=description)

    # first numeric line the server sends
    @utils.hook("raw.received.001", default_event=True)
    def handle_001(self, event):
        event["server"].socket.set_write_throttling(True)
        event["server"].name = event["prefix"].hostmask
        event["server"].set_own_nickname(event["args"][0])
        event["server"].send_whois(event["server"].nickname)

    # server telling us what it supports
    @utils.hook("raw.received.005")
    def handle_005(self, event):
        isupport_list = event["args"][1:-1]

        isupport = {}
        for i, item in enumerate(isupport_list):
            key, sep, value = item.partition("=")
            if value:
                for match in RE_ISUPPORT_ESCAPE.finditer(value):
                    char = codecs.decode(match.group(1), "hex").decode("ascii")
                    value.replace(match.group(0), char)

            if sep:
                isupport[key] = value
            else:
                isupport[key] = None
        event["server"].isupport.update(isupport)

        if "NAMESX" in isupport and not "multi-prefix" in event[
                "server"].agreed_capabilities:
            event["server"].send("PROTOCTL NAMESX")

        if "PREFIX" in isupport:
            modes, symbols = isupport["PREFIX"][1:].split(")", 1)
            event["server"].prefix_symbols.clear()
            event["server"].prefix_modes.clear()
            for symbol, mode in zip(symbols, modes):
                event["server"].prefix_symbols[symbol] = mode
                event["server"].prefix_modes[mode] = symbol

        if "CHANMODES" in isupport:
            modes = isupport["CHANMODES"].split(",", 3)
            event["server"].channel_list_modes = list(modes[0])
            event["server"].channel_paramatered_modes = list(modes[1])
            event["server"].channel_setting_modes = list(modes[2])
            event["server"].channel_modes = list(modes[3])
        if "CHANTYPES" in isupport:
            event["server"].channel_types = list(isupport["CHANTYPES"])
        if "CASEMAPPING" in isupport:
            event["server"].case_mapping = isupport["CASEMAPPING"]

        self._event(event, "numeric.005", isupport=isupport,
            server=event["server"])

    # whois respose (nickname, username, realname, hostname)
    @utils.hook("raw.received.311", default_event=True)
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
    @utils.hook("raw.received.332")
    def handle_332(self, event):
        channel = event["server"].channels.get(event["args"][1])
        topic = event["args"].get(2)
        channel.set_topic(topic)
        self._event(event, "numeric.332", channel=channel,
            server=event["server"], topic=topic)

    # channel topic changed
    @utils.hook("raw.received.topic")
    def topic(self, event):
        user = event["server"].get_user(event["prefix"].nickname)
        channel = event["server"].channels.get(event["args"][0])
        topic = event["args"].get(1)
        channel.set_topic(topic)
        self._event(event, "topic", channel=channel, server=event["server"],
            topic=topic, user=user)

    # on-join channel topic set by/at
    @utils.hook("raw.received.333")
    def handle_333(self, event):
        channel = event["server"].channels.get(event["args"][1])

        topic_setter_hostmask = event["args"][2]
        topic_setter = utils.irc.seperate_hostmask(topic_setter_hostmask)
        topic_time = int(event["args"][3]) if event["args"][3].isdigit(
            ) else None

        channel.set_topic_setter(topic_setter.nickname, topic_setter.username,
            topic_setter.hostname)
        channel.set_topic_time(topic_time)
        self._event(event, "numeric.333", channel=channel,
            setter=topic_setter.nickname, set_at=topic_time,
            server=event["server"])

    # /names response, also on-join user list
    @utils.hook("raw.received.353", default_event=True)
    def handle_353(self, event):
        channel = event["server"].channels.get(event["args"][2])
        nicknames = event["args"].get(3).split()
        for nickname in nicknames:
            modes = set([])

            while nickname[0] in event["server"].prefix_symbols:
                modes.add(event["server"].prefix_symbols[nickname[0]])
                nickname = nickname[1:]

            if "userhost-in-names" in event["server"].agreed_capabilities:
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
    @utils.hook("raw.received.366", default_event=True)
    def handle_366(self, event):
        event["server"].send_whox(event["args"][1], "n", "ahnrtu", "111")

    @utils.hook("raw.received.375")
    def motd_start(self, event):
        event["server"].motd_lines.clear()
        event["server"].motd_lines.append(event["args"][1])

    @utils.hook("raw.received.372")
    def motd_line(self, event):
        event["server"].motd_lines.append(event["args"][1])

    # on user joining channel
    @utils.hook("raw.received.join")
    def join(self, event):
        account = None
        realname = None
        channel_name = event["args"][0]

        if len(event["args"]) == 3:
            if not event["args"][1] == "*":
                account = event["args"][1]
            realname = event["args"][2]

        if not event["server"].is_own_nickname(event["prefix"].nickname):
            channel = event["server"].channels.get(channel_name)
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
            self._event(event, "join", channel=channel, user=user,
                server=event["server"], account=account, realname=realname)
        else:
            channel = event["server"].channels.add(channel_name)
            if channel.name in event["server"].attempted_join:
                del event["server"].attempted_join[channel.name]
            self.events.on("self.join").call(channel=channel,
                server=event["server"], account=account, realname=realname)
            channel.send_mode()

    # on user parting channel
    @utils.hook("raw.received.part")
    def part(self, event):
        channel = event["server"].channels.get(event["args"][0])
        reason = event["args"].get(1)

        if not event["server"].is_own_nickname(event["prefix"].nickname):
            user = event["server"].get_user(event["prefix"].nickname)
            self._event(event, "part", channel=channel, reason=reason,
                user=user, server=event["server"])
            channel.remove_user(user)
            user.part_channel(channel)
            if not len(user.channels):
                event["server"].remove_user(user)
        else:
            self.events.on("self.part").call(channel=channel, reason=reason,
                server=event["server"])
            event["server"].channels.remove(channel)

    # unknown command sent by us, oops!
    @utils.hook("raw.received.421", default_event=True)
    def handle_421(self, event):
        self.bot.log.warn("We sent an unknown command: %s", [event["args"][1]])

    # a user has disconnected!
    @utils.hook("raw.received.quit")
    @utils.hook("raw.send.quit")
    def quit(self, event):
        nickname = None
        if event["direction"] == Direction.RECV:
            nickname = event["prefix"].nickname
        reason = event["args"].get(0)

        if event["direction"] == Direction.RECV:
            nickname = event["prefix"].nickname
            if (not event["server"].is_own_nickname(nickname) and
                    not event["prefix"].hostmask == "*"):
                user = event["server"].get_user(nickname)
                event["server"].remove_user(user)
                self.events.on("received.quit").call(reason=reason, user=user,
                    server=event["server"])
            else:
                event["server"].disconnect()
        else:
            self.events.on("send.quit").call(reason=reason,
                server=event["server"])

    def _match_caps(self, capabilities):
        return set(capabilities) & CAPABILITIES

    # the server is telling us about its capabilities!
    @utils.hook("raw.received.cap")
    def cap(self, event):
        capabilities = utils.parse.keyvalue(event["args"][-1])
        subcommand = event["args"][1].lower()
        is_multiline = len(event["args"]) > 3 and event["args"][2] == "*"

        if subcommand == "ls":
            event["server"].cap_started = True
            event["server"].server_capabilities.update(capabilities)
            if not is_multiline:
                matched_caps = self._match_caps(
                    list(event["server"].server_capabilities.keys()))
                blacklisted_caps = event["server"].get_setting(
                    "blacklisted-caps", [])
                matched_caps = list(
                    set(matched_caps)-set(blacklisted_caps))

                event["server"].queue_capabilities(matched_caps)

                self._event(event, "cap.ls",
                    capabilities=event["server"].server_capabilities,
                    server=event["server"])

                if event["server"].has_capability_queue():
                    event["server"].send_capability_queue()
                else:
                    event["server"].send_capability_end()
        elif subcommand == "new":
            capabilities_keys = capabilities.keys()
            event["server"].server_capabilities.update(capabilities)

            matched_caps = self._match_caps(list(capabilities_keys))
            event["server"].queue_capabilities(matched_caps)

            self._event(event, "cap.new", server=event["server"],
                capabilities=capabilities)

            if event["server"].has_capability_queue():
                event["server"].send_capability_queue()
        elif subcommand == "del":
            for capability in capabilities.keys():
                event["server"].agreed_capabilities.discard(capability)
                del event["server"].server_capabilities[capability]

            self._event(event, "cap.del", server=event["server"],
                capabilities=capabilities)
        elif subcommand == "ack":
            event["server"].agreed_capabilities.update(capabilities)
            self._event(event, "cap.ack", capabilities=capabilities,
               server=event["server"])

        if subcommand == "ack" or subcommand == "nak":
            for capability in capabilities:
                event["server"].requested_capabilities.remove(capability)

            if (event["server"].cap_started and
                    not event["server"].requested_capabilities and
                    not event["server"].waiting_for_capabilities()):
                event["server"].cap_started = False
                event["server"].send_capability_end()

    # the server is asking for authentication
    @utils.hook("raw.received.authenticate")
    def authenticate(self, event):
        self._event(event, "authenticate", message=event["args"][0],
            server=event["server"])

    # someone has changed their nickname
    @utils.hook("raw.received.nick")
    def nick(self, event):
        new_nickname = event["args"].get(0)
        if not event["server"].is_own_nickname(event["prefix"].nickname):
            user = event["server"].get_user(event["prefix"].nickname)
            old_nickname = user.nickname
            user.set_nickname(new_nickname)
            event["server"].change_user_nickname(old_nickname, new_nickname)

            self._event(event, "nick", new_nickname=new_nickname,
                old_nickname=old_nickname, user=user, server=event["server"])
        else:
            old_nickname = event["server"].nickname
            event["server"].set_own_nickname(new_nickname)

            self.events.on("self.nick").call(server=event["server"],
                new_nickname=new_nickname, old_nickname=old_nickname)

    # something's mode has changed
    @utils.hook("raw.received.mode")
    def mode(self, event):
        user = event["server"].get_user(event["prefix"].nickname)
        target = event["args"][0]
        is_channel = target[0] in event["server"].channel_types
        if is_channel:
            channel = event["server"].channels.get(target)
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
                    elif (mode in event["server"].channel_list_modes or
                            mode in event["server"].channel_paramatered_modes):
                        args.pop(0)
                    elif not remove:
                        args.pop(0)
            self._event(event, "mode.channel", modes=modes, mode_args=_args,
                channel=channel, server=event["server"], user=user)
        elif event["server"].is_own_nickname(target):
            modes = RE_MODES.findall(event["args"][1])
            for chunk in modes:
                remove = chunk[0] == "-"
                for mode in chunk[1:]:
                    event["server"].change_own_mode(remove, mode)
            self.events.on("self.mode").call(modes=modes,
                server=event["server"])
            event["server"].send_who(event["server"].nickname)

    # someone (maybe me!) has been invited somewhere
    @utils.hook("raw.received.invite")
    def invite(self, event):
        target_channel = event["args"][1]
        user = event["server"].get_user(event["prefix"].nickname)
        target_user = event["server"].get_user(event["args"][0])
        self._event(event, "invite", user=user, target_channel=target_channel,
            server=event["server"], target_user=target_user)

    # we've received/sent a message
    @utils.hook("raw.received.privmsg")
    @utils.hook("raw.send.privmsg")
    def privmsg(self, event):
        if event["direction"] == Direction.SEND:
            from_self = True
            if "echo-message" in event["server"].agreed_capabilities:
                return
        else:
            if event["prefix"]:
                from_self = event["server"].is_own_nickname(
                    event["prefix"].nickname)
            else:
                from_self = False

        user = None
        if "prefix" in event:
            user = event["server"].get_user(event["prefix"].nickname)

        message = event["args"][1]
        target = event["args"][0]

        # strip prefix_symbols from the start of target, for when people use
        # e.g. 'PRIVMSG +#channel :hi' which would send a message to only
        # voiced-or-above users
        statusmsg = []
        while target[0] in event["server"].prefix_symbols.keys():
            statusmsg.append(target[0])
            target = target[1:]

        channel = None
        if target[0] in event["server"].channel_types:
            if not target in event["server"].channels:
                return
            channel = event["server"].channels.get(target)

        action = False
        event_type = "message"
        ctcp_message = utils.irc.parse_ctcp(message)
        if ctcp_message:
            message = ctcp_message.message
            event_type = "ctcp.%s" % ctcp_message.command
            if ctcp_message.command == "ACTION":
                action = True
                message = ctcp_message.message

        if user and "account" in event["tags"]:
            user.identified_account = event["tags"]["account"]
            user.identified_account_id = event["server"].get_user(
                event["tags"]["account"]).get_id()

        kwargs = {"message": message, "message_split": message.split(),
            "server": event["server"], "tags": event["tags"],
            "action": action}

        direction = "send" if from_self else "received"
        context = "channel" if channel else "private"
        hook = self.events.on(direction).on(event_type).on(context)

        user_nickname = None
        if user:
            user_nickname = None if from_self else user.nickname

        if channel:
            hook.call(user=user, channel=channel, statusmsg=statusmsg, **kwargs)
            channel.buffer.add_message(user_nickname, message, action,
                event["tags"], user==None)
        elif event["server"].is_own_nickname(target):
            hook.call(user=user, **kwargs)
            user.buffer.add_message(user_nickname, message, action,
                event["tags"], False)
        elif not "prefix" in event:
            # a message we've sent to a user
            user = event["server"].get_user(target)
            hook.call(user=user, **kwargs)
            user.buffer.add_message(user_nickname, message, action,
                event["tags"], True)

    # we've received/sent a notice
    @utils.hook("raw.received.notice")
    @utils.hook("raw.send.notice")
    def notice(self, event):
        if event["direction"] == Direction.SEND:
            from_self = True
            if "echo-message" in event["server"].agreed_capabilities:
                return
        else:
            if event["prefix"]:
                from_self = event["server"].is_own_nickname(
                    event["prefix"].nickname)
            else:
                from_self = False

        message = event["args"][1]
        message_split = message.split(" ")
        target = event["args"][0]

        if "prefix" in event and (
                not event["prefix"] or
                not event["server"].name or
                event["prefix"].hostmask == event["server"].name or
                target == "*"):
            if event["prefix"]:
                event["server"].name = event["prefix"].hostmask

            self._event(event, "server-notice", message=message,
                message_split=message_split, server=event["server"])
        else:
            user = None
            if "prefix" in event:
                user = event["server"].get_user(event["prefix"].nickname)

            channel = None
            if target[0] in event["server"].channel_types:
                channel = event["server"].channels.get(target)

            direction = "send" if from_self else "received"
            context = "channel" if channel else "private"
            hook = self.events.on(direction).on("notice").on(context)

            user_nickname = None
            if user:
                user_nickname = None if from_self else user.nickname

            kwargs = {"message": message, "message_split": message_split,
                "server": event["server"], "tags": event["tags"]}

            if channel:
                hook.call(user=user, channel=channel, **kwargs)
                channel.buffer.add_notice(user_nickname, message, event["tags"],
                    user==None)
            elif event["server"].is_own_nickname(target):
                hook.call(user=user, **kwargs)
                user.buffer.add_notice(user_nickname, message, event["tags"],
                    False)
            elif not "prefix" in event:
                # a notice we've sent to a user
                user = event["server"].get_user(target)
                hook.call(user=user, **kwargs)
                user.buffer.add_notice(user_nickname, message, event["tags"],
                    True)

    # IRCv3 TAGMSG, used to send tags without any other information
    @utils.hook("raw.received.tagmsg")
    def tagmsg(self, event):
        user = event["server"].get_user(event["prefix"].nickname)
        target = event["args"][0]

        if target[0] in event["server"].channel_types:
            channel = event["server"].channels.get(target)
            self._event(event, "tagmsg.channel", channel=channel, user=user,
                tags=event["tags"], server=event["server"])
        elif event["server"].is_own_nickname(target):
            self._event(event, "tagmsg.private", user=user, tags=event["tags"],
                server=event["server"])

    # IRCv3 AWAY, used to notify us that a client we can see has changed /away
    @utils.hook("raw.received.away")
    def away(self, event):
        user = event["server"].get_user(event["prefix"].nickname)
        message = event["args"].get(0)
        if message:
            user.away = True
            self._event(event, "away.on", user=user, server=event["server"],
                message=message)
        else:
            user.away = False
            self._event(event, "away.off", user=user, server=event["server"])

    @utils.hook("raw.received.batch")
    def batch(self, event):
        identifier = event["args"][0]
        modifier, identifier = identifier[0], identifier[1:]
        batch_type = event["args"][1]

        if modifier == "+":
            event["server"].batches[identifier] = utils.irc.IRCRecvBatch(
                identifier, batch_type, event["tags"])
        else:
            batch = event["server"].batches[identifier]
            del event["server"].batches[identifier]

            add_tags = {}
            if batch.type in LABELED_BATCH.keys():
                tag_name = LABELED_BATCH[batch.type]
                add_tags[tag_name] = batch.tags[tag_name]

            for line in batch.lines:
                if add_tags:
                    line.tags.update(add_tags)
                self._handle(line)

    # IRCv3 CHGHOST, a user's username and/or hostname has changed
    @utils.hook("raw.received.chghost")
    def chghost(self, event):
        nickname = event["prefix"].nickname
        username = event["args"][0]
        hostname = event["args"][1]

        if not event["server"].is_own_nickname(nickname):
            target = event["server"].get_user(nickname)
        else:
            target = event["server"]
        target.username = username
        target.hostname = hostname

    # IRCv3 SETNAME, to change a user's realname
    @utils.hook("raw.received.setname")
    def setname(self, event):
        user = event["server"].get_user(event["prefix"].nickname)
        user.realname = event["args"][0]

    @utils.hook("raw.received.account")
    def account(self, event):
        user = event["server"].get_user(event["prefix"].nickname)

        if not event["args"][0] == "*":
            user.identified_account = event["args"][0]
            user.identified_account_id = event["server"].get_user(
                event["args"][0]).get_id()
            self._event(event, "account.login", user=user,
                server=event["server"], account=event["args"][0])
        else:
            user.identified_account = None
            user.identified_account_id = None
            self._event(event, "account.logout", user=user,
                server=event["server"])

    # response to a WHO command for user information
    @utils.hook("raw.received.352", default_event=True)
    def handle_352(self, event):
        nickname = event["args"][5]
        if not event["server"].is_own_nickname(nickname):
            target = event["server"].get_user(nickname)
        else:
            target = event["server"]
        target.username = event["args"][2]
        target.hostname = event["args"][3]

    # response to a WHOX command for user information, including account name
    @utils.hook("raw.received.354", default_event=True)
    def handle_354(self, event):
        if event["args"][1] == "111":
            nickname = event["args"][4]

            if not event["server"].is_own_nickname(nickname):
                target = event["server"].get_user(nickname)

                account = event["args"][5]
                if not account == "0":
                    target.identified_account = account
                else:
                    target.identified_account = None
            else:
                target = event["server"]

            target.username = event["args"][2]
            target.hostname = event["args"][3]
            target.realname = event["args"][6]


    # response to an empty mode command
    @utils.hook("raw.received.324", default_event=True)
    def handle_324(self, event):
        channel = event["server"].channels.get(event["args"][1])
        modes = event["args"][2]
        if modes[0] == "+" and modes[1:]:
            for mode in modes[1:]:
                if mode in event["server"].channel_modes:
                    channel.add_mode(mode)

    # channel creation unix timestamp
    @utils.hook("raw.received.329", default_event=True)
    def handle_329(self, event):
        channel = event["server"].channels.get(event["args"][1])
        channel.creation_timestamp = int(event["args"][2])

    # nickname already in use
    @utils.hook("raw.received.433", default_event=True)
    def handle_433(self, event):
        new_nick = "%s|" % event["server"].connection_params.nickname
        event["server"].send_nick(new_nick)

    # we need a registered nickname for this channel
    @utils.hook("raw.received.477", default_event=True)
    def handle_477(self, event):
        channel_name = event["server"].irc_lower(event["args"][1])
        if channel_name in event["server"].channels:
            key = event["server"].attempted_join[channel_name]
            self.timers.add("rejoin", 5, channel_name=channe_name, key=key,
                server_id=event["server"].id)

    # someone's been kicked from a channel
    @utils.hook("raw.received.kick")
    def kick(self, event):
        user = event["server"].get_user(event["prefix"].nickname)
        target = event["args"][1]
        channel = event["server"].channels.get(event["args"][0])
        reason = event["args"].get(2)

        if not event["server"].is_own_nickname(target):
            target_user = event["server"].get_user(target)
            self._event(event, "kick", channel=channel, reason=reason,
                target_user=target_user, user=user, server=event["server"])

            channel.remove_user(target_user)
            target_user.part_channel(channel)
            if not len(target_user.channels):
                event["server"].remove_user(target_user)
        else:
            event["server"].channels.remove(channel)
            self.events.on("self.kick").call(channel=channel, reason=reason,
                user=user, server=event["server"])

    # a channel has been renamed
    @utils.hook("raw.received.rename")
    def rename(self, event):
        old_name = event["args"][0]
        new_name = event["args"][1]
        channel = event["server"].channels.get(old_name)

        event["server"].channels.rename(old_name, new_name)
        self._event(event, "rename", channel=channel, old_name=old_name,
            new_name=new_name, reason=event["args"].get(2),
            server=event["server"])
