import uuid
from src import ModuleManager, utils

CAP = utils.irc.Capability(None, "draft/labeled-response-0.2",
    alias="labeled-response", depends_on=["batch"])
TAG = utils.irc.MessageTag(None, "draft/label")
BATCH = utils.irc.BatchType(None, "draft/labeled-response")

CAP_TO_TAG = {
    "draft/labeled-response-0.2": "draft/label"
}

class WaitingForLabel(object):
    def __init__(self, line, events):
        self.line = line
        self.events = events
        self.labels_since = 0

@utils.export("cap", CAP)
class Module(ModuleManager.BaseModule):
    @utils.hook("new.server")
    def new_server(self, event):
        event["server"]._label_cache = {}

    @utils.hook("preprocess.send")
    def raw_send(self, event):
        available_cap = event["server"].available_capability(CAP)

        if available_cap:
            label = TAG.get_value(event["line"].tags)
            if label == None:
                tag_key = CAP_TO_TAG[available_cap]
                label = str(uuid.uuid4())
                event["line"].tags[tag_key] = label

            event["server"]._label_cache[label] = WaitingForLabel(event["line"],
                event["events"])

    @utils.hook("raw.received")
    def raw_recv(self, event):
        if not event["line"].command == "BATCH":
            label = TAG.get_value(event["line"].tags)
            if not label == None:
                self._recv(event["server"], label, [event["line"]])

    @utils.hook("received.batch.end")
    def batch_end(self, event):
        if BATCH.match(event["batch"].type):
            label = TAG.get_value(event["batch"].tags)
            self._recv(event["server"], label, event["batch"].get_lines())

    def _recv(self, server, label, lines):
        if not label in server._label_cache:
            self.log.debug("unknown label received on %s: %s",
                [str(server), label])
            return

        cached = server._label_cache.pop(label)
        cached.events.on("labeled-response").call(line=cached.line,
            responses=lines)

        for label, other_cached in server._label_cache.items():
            other_cached.labels_since += 1
            if other_cached.labels_since == 10:
                self.log.debug(
                    "%d labels seen while waiting for response to %s on %s",
                    [other_cached.labels_since, label, str(server)])
