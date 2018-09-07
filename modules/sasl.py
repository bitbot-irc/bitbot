import base64

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        events.on("received.cap.ls").hook(self.on_cap)
        events.on("received.cap.ack").hook(self.on_cap_ack)
        events.on("received.authenticate").hook(self.on_authenticate)
        events.on("received.numeric.903").hook(self.sasl_success)

    def on_cap(self, event):
        has_sasl = "sasl" in event["capabilities"]
        has_mechanisms = has_sasl and not event["capabilities"]["sasl"
            ] == None
        has_plaintext = has_mechanisms and "PLAIN" in event["capabilities"
            ]["sasl"].split(",")

        if has_sasl and (has_plaintext or not has_mechanisms) and event[
                "server"].get_setting("sasl", None):
            event["server"].queue_capability("sasl")

    def on_cap_ack(self, event):
        if "sasl" in event["capabilities"]:
            event["server"].send_authenticate("PLAIN")
            event["server"].wait_for_capability("sasl")

    def on_authenticate(self, event):
        if event["message"] != "+":
            event["server"].send_authenticate("*")
        else:
            sasl_nick, sasl_pass = event["server"].get_setting("sasl")
            auth_text = "%s\0%s\0%s" % (
                sasl_nick, sasl_nick, sasl_pass)
            auth_text = base64.b64encode(auth_text.encode("utf8"))
            auth_text = auth_text.decode("utf8")
            event["server"].send_authenticate(auth_text)

    def sasl_success(self, event):
        event["server"].capability_done("sasl")
