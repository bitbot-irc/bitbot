

class Module(object):
	def __init__(self, bot):
		bot.events.on("received").on("numeric").on("001"
			).hook(self.on_connect)

	def on_connect(self, event):
		nickserv_password = event["server"].get_setting(
			"nickserv-password")
		if nickserv_password:
			event["server"].send_message("nickserv",
				"identify %s" % nickserv_password)
