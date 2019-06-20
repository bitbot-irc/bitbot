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
    utils.irc.Capability(None, "draft/rename"),
    utils.irc.Capability(None, "draft/setname")
]

def _cap_match(server, caps):
    matched_caps = {}
    blacklist = server.get_setting("blacklisted-caps", [])
    for cap in caps:
        available = cap.available(server.server_capabilities)
        if (available and not server.has_capability(cap) and
                not available in blacklist):
            matched_caps[available] = cap
    return matched_caps

def cap(exports, events, event):
    capabilities = utils.parse.keyvalue(event["args"][-1])
    subcommand = event["args"][1].upper()
    is_multiline = len(event["args"]) > 3 and event["args"][2] == "*"

    if subcommand == "DEL":
        for capability in capabilities.keys():
            event["server"].agreed_capabilities.discard(capability)
            del event["server"].server_capabilities[capability]

        events.on("received.cap.del").call(server=event["server"],
            capabilities=capabilities)
    elif subcommand == "ACK":
        event["server"].agreed_capabilities.update(capabilities)
        events.on("received.cap.ack").call(capabilities=capabilities,
           server=event["server"])

    if subcommand == "LS" or subcommand == "NEW":
        event["server"].server_capabilities.update(capabilities)
        if not is_multiline:
            server_caps = list(event["server"].server_capabilities.keys())
            all_caps = CAPABILITIES[:]

            export_caps = [cap.copy() for cap in exports.get_all("cap")]
            all_caps.extend(export_caps)

            module_caps = events.on("received.cap.ls").call(
                capabilities=event["server"].server_capabilities,
                server=event["server"])
            module_caps = list(filter(None, module_caps))
            all_caps.extend(module_caps)

            matched_caps = _cap_match(event["server"], all_caps)
            event["server"].capability_queue.update(matched_caps)

            if event["server"].capability_queue:
                event["server"].send_capability_queue()
            else:
                event["server"].send_capability_end()


    if subcommand == "ACK" or subcommand == "NAK":
        ack = subcommand == "ACK"
        for capability in capabilities:
            cap_obj = event["server"].capabilities_requested[capability]
            del event["server"].capabilities_requested[capability]
            if ack:
                cap_obj.ack()
            else:
                cap_obj.nak()

        if (not event["server"].capabilities_requested and
                not event["server"].waiting_for_capabilities()):
            event["server"].send_capability_end()

def authenticate(events, event):
    events.on("received.authenticate").call(message=event["args"][0],
        server=event["server"])
