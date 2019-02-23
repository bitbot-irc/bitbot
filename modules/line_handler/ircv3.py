from src import utils

CAPABILITIES = {"multi-prefix", "chghost", "invite-notify", "account-tag",
    "account-notify", "extended-join", "away-notify", "userhost-in-names",
    "draft/message-tags-0.2", "message-tags", "server-time", "cap-notify",
    "batch", "draft/labeled-response", "draft/rename", "echo-message",
    "draft/setname"}

def _match_caps(capabilities):
    return set(capabilities) & CAPABILITIES

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
