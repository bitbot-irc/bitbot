import enum
from src import EventManager, ModuleManager, utils
from . import channel, core, ircv3, message, user

LABELED_BATCH = {
    "labeled-response": "label",
    "draft/labeled-response": "draft/label"
}

class Module(ModuleManager.BaseModule):
    def _handle(self, server, line):
        hooks = self.events.on("raw.received").on(line.command).get_hooks()
        default_events = []
        for hook in hooks:
            default_events.append(hook.kwargs.get("default_event", False))
        default_event = any(default_events)

        kwargs = {"args": line.args, "tags": line.tags, "server": server,
            "prefix": line.prefix, "direction": utils.Direction.RECV}

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
        self.events.on("raw.send").on(event["line"].command).call_unsafe(
            args=event["line"].args, tags=event["line"].tags,
            server=event["server"], direction=utils.Direction.SEND)

    # ping from the server
    @utils.hook("raw.received.ping")
    def ping(self, event):
        core.ping(event)

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
        core.handle_001(event)

    # server telling us what it supports
    @utils.hook("raw.received.005")
    def handle_005(self, event):
        core.handle_005(self.events, event)

    # whois respose (nickname, username, realname, hostname)
    @utils.hook("raw.received.311", default_event=True)
    def handle_311(self, event):
        user.handle_311(event)

    # on-join channel topic line
    @utils.hook("raw.received.332")
    def handle_332(self, event):
        channel.handle_332(self.events, event)

    # channel topic changed
    @utils.hook("raw.received.topic")
    def topic(self, event):
        channel.topic(self.events, event)

    # on-join channel topic set by/at
    @utils.hook("raw.received.333")
    def handle_333(self, event):
        channel.handle_333(self.events, event)

    # /names response, also on-join user list
    @utils.hook("raw.received.353", default_event=True)
    def handle_353(self, event):
        channel.handle_353(event)

    # on-join user list has finished
    @utils.hook("raw.received.366", default_event=True)
    def handle_366(self, event):
        channel.handle_366(event)

    @utils.hook("raw.received.375", priority=EventManager.PRIORITY_HIGH)
    def motd_start(self, event):
        core.motd_start(event)

    @utils.hook("raw.received.372")
    @utils.hook("raw.received.375")
    def motd_line(self, event):
        core.motd_line(event)

    # on user joining channel
    @utils.hook("raw.received.join")
    def join(self, event):
        channel.join(self.events, event)

    # on user parting channel
    @utils.hook("raw.received.part")
    def part(self, event):
        channel.part(self.events, event)

    # unknown command sent by us, oops!
    @utils.hook("raw.received.421", default_event=True)
    def handle_421(self, event):
        self.bot.log.warn("We sent an unknown command: %s", [event["args"][1]])

    # a user has disconnected!
    @utils.hook("raw.received.quit")
    @utils.hook("raw.send.quit")
    def quit(self, event):
        user.quit(self.events, event)

    # the server is telling us about its capabilities!
    @utils.hook("raw.received.cap")
    def cap(self, event):
        ircv3.cap(self.events, event)

    # the server is asking for authentication
    @utils.hook("raw.received.authenticate")
    def authenticate(self, event):
        ircv3.authenticate(self.events, event)

    # someone has changed their nickname
    @utils.hook("raw.received.nick")
    def nick(self, event):
        user.nick(self.events, event)

    # something's mode has changed
    @utils.hook("raw.received.mode")
    def mode(self, event):
        core.mode(self.events, event)

    # someone (maybe me!) has been invited somewhere
    @utils.hook("raw.received.invite")
    def invite(self, event):
        core.invite(self.events, event)

    # we've received/sent a message
    @utils.hook("raw.received.privmsg")
    @utils.hook("raw.send.privmsg")
    def privmsg(self, event):
        message.privmsg(self.events, event)

    # we've received/sent a notice
    @utils.hook("raw.received.notice")
    @utils.hook("raw.send.notice")
    def notice(self, event):
        message.notice(self.events, event)

    # IRCv3 TAGMSG, used to send tags without any other information
    @utils.hook("raw.received.tagmsg")
    def tagmsg(self, event):
        message.tagmsg(self.events, event)

    # IRCv3 AWAY, used to notify us that a client we can see has changed /away
    @utils.hook("raw.received.away")
    def away(self, event):
        user.away(self.events, event)

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
        user.chghost(event)

    # IRCv3 SETNAME, to change a user's realname
    @utils.hook("raw.received.setname")
    def setname(self, event):
        user.setname(event)

    @utils.hook("raw.received.account")
    def account(self, event):
        user.account(self.events, event)

    # response to a WHO command for user information
    @utils.hook("raw.received.352", default_event=True)
    def handle_352(self, event):
        core.handle_352(event)

    # response to a WHOX command for user information, including account name
    @utils.hook("raw.received.354", default_event=True)
    def handle_354(self, event):
        core.handle_354(event)


    # response to an empty mode command
    @utils.hook("raw.received.324", default_event=True)
    def handle_324(self, event):
        channel.handle_324(event)

    # channel creation unix timestamp
    @utils.hook("raw.received.329", default_event=True)
    def handle_329(self, event):
        channel.handle_329(event)

    # nickname already in use
    @utils.hook("raw.received.433", default_event=True)
    def handle_433(self, event):
        core.handle_433(event)

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
        channel.kick(self.events, event)

    # a channel has been renamed
    @utils.hook("raw.received.rename")
    def rename(self, event):
        channel.rename(self.events, event)
