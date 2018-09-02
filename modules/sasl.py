import base64

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        events.on("preprocess.connect").hook(self.preprocess_connect)
        events.on("received.cap").hook(self.on_cap)
        events.on("received.authenticate").hook(self.on_authenticate)
        events.on("received.numeric").on(
            "902", "903", "904", "905", "906", "907", "908").hook(self.on_90x)

    def preprocess_connect(self, event):
        sasl = event["server"].get_setting("sasl")
        if sasl:
            event["server"].send_capability_request("sasl")

    def on_cap(self, event):
        if event["subcommand"] == "NAK":
            event["server"].send_capability_end()
        elif event["subcommand"] == "ACK":
            if not "sasl" in event["capabilities"]:
                event["server"].send_capability_end()
            else:
                event["server"].send_authenticate("PLAIN")

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

    def on_90x(self, event):
        event["server"].send_capability_end()

