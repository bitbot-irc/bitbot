import uuid
from src import ModuleManager, utils

CAP = utils.irc.Capability(None, "draft/labeled-response-0.2")
TAG = utils.irc.MessageTag(None, "draft/label")

CAP_TO_TAG = {
    "draft/labeled-response-0.2": "draft/label"
}

class Module(ModuleManager.BaseModule):
    @utils.hook("new.server")
    def new_server(self, event):
        event["server"]._label_cache = {}

    @utils.hook("received.cap.ls")
    @utils.hook("received.cap.new")
    def on_cap(self, event):
        if CAP.available(event["capabilities"]):
            return CAP.copy()

    @utils.hook("preprocess.send")
    def raw_send(self, event):
        available_cap = event["server"].available_capability(CAP)

        if available_cap:
            label = TAG.get_value(event["line"].tags)
            if label == None:
                tag_key = CAP_TO_TAG[available_cap]
                label = str(uuid.uuid4())
                event["line"].tags[tag_key] = label

            event["server"]._label_cache[label] = event["line"]

    @utils.hook("raw.received")
    def raw_recv(self, event):
        if not event["line"].command == "BATCH":
            label = TAG.get_value(event["line"].tags)
            if not label == None:
                self._recv(event["server"], label, event["line"])

    @utils.hook("received.batch.end")
    def batch_end(self, event):
        if TAG.match(event["batch"].type):
            self._recv(event["server"], event["batch"].identifier, None)

    def _recv(self, server, label, line):
        cached_line = server._label_cache.pop(label)
        # do something with the line!
