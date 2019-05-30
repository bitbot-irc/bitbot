from src import utils

CAPABILITIES = [
    utils.irc.Capability("multi-prefix"),
    utils.irc.Capability("chghost"),
    utils.irc.Capability("invite-notify"),
    utils.irc.Capability("account-tag"),
    utils.irc.Capability("account-notify"),
    utils.irc.Capability("extended-join"),
    utils.irc.Capability("away-notify"),
    utils.irc.Capability("userhost-in-names"),
    utils.irc.Capability("message-tags", "draft/message-tags-0.2"),
    utils.irc.Capability("cap-notify"),
    utils.irc.Capability("batch"),
    utils.irc.Capability("echo-message"),
    utils.irc.Capability(None, "draft/labeled-response-0.2"),
    utils.irc.Capability(None, "draft/rename"),
    utils.irc.Capability(None, "draft/setname")
]

def _match_caps(our_capabilities, offered_capabilities):
    matched = {}
    for capability in our_capabilities:
        available = capability.available(offered_capabilities)
        if available:
            matched[available] = capability
    return matched

def _caps_offered(server, caps):
    blacklist = server.get_setting("blacklisted-caps", [])
    for cap_name, cap in caps.items():
        if not cap_name in blacklist:
            server.capability_queue[cap_name] = cap

def cap(events, event):
    capabilities = utils.parse.keyvalue(event["args"][-1])
    subcommand = event["args"][1].upper()
    is_multiline = len(event["args"]) > 3 and event["args"][2] == "*"

    if subcommand == "LS":
        event["server"].cap_started = True
        event["server"].server_capabilities.update(capabilities)
        if not is_multiline:
            server_caps = list(event["server"].server_capabilities.keys())
            matched_caps = _match_caps(CAPABILITIES, server_caps)

            module_caps = events.on("received.cap.ls").call(
                capabilities=event["server"].server_capabilities,
                server=event["server"])
            module_caps = list(filter(None, module_caps))
            matched_caps.update(_match_caps(module_caps, server_caps))

            _caps_offered(event["server"], matched_caps)

            if event["server"].capability_queue:
                event["server"].send_capability_queue()
            else:
                event["server"].send_capability_end()
    elif subcommand == "NEW":
        capabilities_keys = capabilities.keys()
        event["server"].server_capabilities.update(capabilities)

        matched_caps = _match_caps(CAPABILITIES, list(capabilities_keys))

        module_caps = events.on("received.cap.new").call(
            server=event["server"], capabilities=capabilities)
        module_caps = list(filter(None, module_caps))
        matched_caps.update(_match_caps(module_caps, capabilities_keys))

        _caps_offered(event["server"], matched_caps)

        if event["server"].capability_queue:
            event["server"].send_capability_queue()
    elif subcommand == "DEL":
        for capability in capabilities.keys():
            event["server"].agreed_capabilities.discard(capability)
            del event["server"].server_capabilities[capability]

        events.on("received.cap.del").call(server=event["server"],
            capabilities=capabilities)
    elif subcommand == "ACK":
        event["server"].agreed_capabilities.update(capabilities)
        events.on("received.cap.ack").call(capabilities=capabilities,
           server=event["server"])

    if subcommand == "ACK" or subcommand == "NAK":
        ack = subcommand == "ACK"
        for capability in capabilities:
            cap_obj = event["server"].capability_queue[capability]
            del event["server"].capability_queue[capability]
            if ack:
                cap_obj.ack()
            else:
                cap_obj.nak()

        if (event["server"].cap_started and
                not event["server"].capability_queue and
                not event["server"].waiting_for_capabilities()):
            event["server"].cap_started = False
            event["server"].send_capability_end()

def authenticate(events, event):
    events.on("received.authenticate").call(message=event["args"][0],
        server=event["server"])
