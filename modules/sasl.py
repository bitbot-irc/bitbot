import base64

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("cap").hook(self.on_cap)
        bot.events.on("received").on("authenticate").hook(self.on_authenticate)
        bot.events.on("received").on("numeric").on(
            "902", "903", "904", "905", "906", "907", "908").hook(self.on_90x)

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

