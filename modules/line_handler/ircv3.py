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
    utils.irc.Capability("server-time"),
    utils.irc.Capability("cap-notify"),
    utils.irc.Capability("batch"),
    utils.irc.Capability("echo-message"),
    utils.irc.Capability(None, "draft/labeled-response"),
    utils.irc.Capability(None, "draft/rename"),
    utils.irc.Capability(None, "draft/setname")
]

def _match_caps(capabilities):
    matched = []
    for capability in CAPABILITIES:
        available = capability.available(capabilities)
        if available:
            matched.append(available)
    return matched

def cap(events, event):
    capabilities = utils.parse.keyvalue(event["args"][-1])
    subcommand = event["args"][1].lower()
    is_multiline = len(event["args"]) > 3 and event["args"][2] == "*"

    if subcommand == "ls":
        event["server"].cap_started = True
        event["server"].server_capabilities.update(capabilities)
        if not is_multiline:
            matched_caps = _match_caps(
                list(event["server"].server_capabilities.keys()))
            blacklisted_caps = event["server"].get_setting(
                "blacklisted-caps", [])
            matched_caps = list(
                set(matched_caps)-set(blacklisted_caps))

            event["server"].queue_capabilities(matched_caps)

            events.on("received.cap.ls").call(
                capabilities=event["server"].server_capabilities,
                server=event["server"])

            if event["server"].has_capability_queue():
                event["server"].send_capability_queue()
            else:
                event["server"].send_capability_end()
    elif subcommand == "new":
        capabilities_keys = capabilities.keys()
        event["server"].server_capabilities.update(capabilities)

        matched_caps = _match_caps(list(capabilities_keys))
        event["server"].queue_capabilities(matched_caps)

        events.on("received.cap.new").call(server=event["server"],
            capabilities=capabilities)

        if event["server"].has_capability_queue():
            event["server"].send_capability_queue()
    elif subcommand == "del":
        for capability in capabilities.keys():
            event["server"].agreed_capabilities.discard(capability)
            del event["server"].server_capabilities[capability]

        events.on("received.cap.del").call(server=event["server"],
            capabilities=capabilities)
    elif subcommand == "ack":
        event["server"].agreed_capabilities.update(capabilities)
        events.on("received.cap.ack").call(capabilities=capabilities,
           server=event["server"])

    if subcommand == "ack" or subcommand == "nak":
        for capability in capabilities:
            event["server"].requested_capabilities.remove(capability)

        if (event["server"].cap_started and
                not event["server"].requested_capabilities and
                not event["server"].waiting_for_capabilities()):
            event["server"].cap_started = False
            event["server"].send_capability_end()

def authenticate(events, event):
    events.on("received.authenticate").call(message=event["args"][0],
        server=event["server"])
