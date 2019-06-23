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
    utils.irc.Capability(None, "draft/rename", alias="rename"),
    utils.irc.Capability(None, "draft/setname", alias="setname")
]

def _cap_depend_sort(caps, server_caps):
    sorted_caps = []

    caps_copy = {alias: cap.copy() for alias, cap in caps.items()}

    for cap in caps.values():
        if not cap.available(server_caps):
            del caps_copy[cap.alias]

    while True:
        remove = []
        for alias, cap in caps_copy.items():
            for depend_alias in cap.depends_on:
                if not depend_alias in caps_copy:
                    remove.append(alias)
        if remove:
            for alias in remove:
                del caps_copy[alias]
        else:
            break

    while caps_copy:
        fulfilled = []
        for cap in caps_copy.values():
            remove = []
            for depend_alias in cap.depends_on:
                if depend_alias in sorted_caps:
                    remove.append(depend_alias)
            for remove_cap in remove:
                cap.depends_on.remove(remove_cap)

            if not cap.depends_on:
                fulfilled.append(cap.alias)
        for fulfilled_cap in fulfilled:
            del caps_copy[fulfilled_cap]
            sorted_caps.append(fulfilled_cap)
    return [caps[alias] for alias in sorted_caps]

def _cap_match(server, caps):
    matched_caps = {}
    blacklist = server.get_setting("blacklisted-caps", [])

    cap_aliases = {}
    for cap in caps:
        if not cap.alias in blacklist:
            cap_aliases[cap.alias] = cap

    sorted_caps = _cap_depend_sort(cap_aliases, server.server_capabilities)

    for cap in sorted_caps:
        available = cap.available(server.server_capabilities)
        if available and not server.has_capability(cap):
            matched_caps[available] = cap
    return matched_caps

def cap(exports, events, event):
    capabilities = utils.parse.keyvalue(event["line"].args[-1])
    subcommand = event["line"].args[1].upper()
    is_multiline = len(event["line"].args) > 3 and event["line"].args[2] == "*"

    if subcommand == "DEL":
        for capability in capabilities.keys():
            event["server"].agreed_capabilities.discard(capability)
            del event["server"].server_capabilities[capability]

        events.on("received.cap.del").call(server=event["server"],
            capabilities=capabilities)
    elif subcommand == "ACK":
        for cap_name, cap_args in capabilities.items():
            if cap_name[0] == "-":
                event["server"].agreed_capabilities.discard(cap_name[1:])
            else:
                event["server"].agreed_capabilities.add(cap_name)

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
            if capability in event["server"].capabilities_requested:
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
    events.on("received.authenticate").call(message=event["line"].args[0],
        server=event["server"])
