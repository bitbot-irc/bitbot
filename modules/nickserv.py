import base64

class Module(object):
    def __init__(self, bot):
        bot.events.on("new").on("server").hook(self.on_new_server)
        bot.events.on("received").on("numeric").on("001"
            ).hook(self.on_connect)
        bot.events.on("received").on("command").on("setnickserv"
            ).hook(self.set_nickserv, min_args=1, permission="setnickserv",
            help="Set bot's nickserv password", usage="<password>",
            private_only=True)
        bot.events.on("received").on("cap").hook(self.on_cap)
        bot.events.on("received").on("authenticate").hook(self.on_authenticate)
        for code in ["902", "903", "904", "905", "906", "907", "908"]:
            bot.events.on("received").on("numeric").on(code).hook(self.on_90x)

    def on_new_server(self, event):
        event["server"].attempted_auth = False
        event["server"].sasl_success = False

    def on_connect(self, event):
        nickserv_password = event["server"].get_setting(
            "nickserv-password")
        if nickserv_password and not event["server"].sasl_success:
            event["server"].attempted_auth = True
            event["server"].send_message("nickserv",
                "identify %s" % nickserv_password)

    def set_nickserv(self, event):
        nickserv_password = event["args"]
        event["server"].set_setting("nickserv-password", nickserv_password)
        event["stdout"].write("Nickserv password saved")

    def on_cap(self, event):
        if event["subcommand"] == "NAK":
            event["server"].send_capability_end()
        elif event["subcommand"] == "ACK":
            event["server"].send_authenticate("PLAIN")
        else:
            pass

    def on_authenticate(self, event):
        if event["message"] != "+":
            event["server"].send_authenticate("*")
        else:
            nick = event["server"].original_nickname
            password = event["server"].get_setting("nickserv-password")
            event["server"].attempted_auth = True
            event["server"].send_authenticate(
                base64.b64encode(("%s\0%s\0%s" % (nick, nick, password)).encode("utf8")).decode("utf8")
            )

    def on_90x(self, event):
        if event["number"]=="903":
            event["server"].sasl_success = True
        event["server"].send_capability_end()
