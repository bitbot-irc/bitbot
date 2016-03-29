

class Module(object):
	def __init__(self, bot):
		bot.events.on("self").on("join").hook(self.on_join)
		bot.events.on("received").on("numeric").on("366").hook(
			self.on_connect)

	def on_join(self, event):
		channels = set(event["server"].get_setting("autojoin", []))
		channels.add(event["channel"].name)
		event["server"].set_setting("autojoin", list(channels))

	def on_connect(self, event):
		if event["line_split"][3].lower() == "#bitbot":
			channels = event["server"].get_setting("autojoin", [])
			for channel in channels:
				event["server"].send_join(channel)
