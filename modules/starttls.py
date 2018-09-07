import base64

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        events.on("received.cap.ls").hook(self.on_cap)
        events.on("received.cap.ack").hook(self.on_cap_ack)

        events.on("received.numeric.670").hook(self.starttls_success)
        events.on("received.numeric.691").hook(self.starttls_failed)

    def on_cap(self, event):
        if "tls" in event["capabilities"].keys() and not event["server"].tls:
            event["server"].queue_capability("tls")

    def on_cap_ack(self, event):
        if "tls" in event["capabilities"].keys():
            event["server"].send_starttls()
            event["server"].wait_for_capability("tls")

    def starttls_success(self, event):
        event["server"].wrap_tls()
        event["server"].capability_done("tls")
    def starttls_failed(self, event):
        event["server"].capability_done("tls")

