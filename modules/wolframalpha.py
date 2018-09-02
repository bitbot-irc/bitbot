#--require-config wolframalpha-api-key
import json
import Utils

URL_WA = "https://api.wolframalpha.com/v1/result"

class Module(object):
    _name = "Wolfram|Alpha"
    def __init__(self, bot, events, exports):
        self.bot = bot
        events.on("received").on("command").on("wolframalpha", "wa"
            ).hook(self.wa, min_args=1, help=
            "Evauate a given string on Wolfram|Alpha",
            usage="<query>")

    def wa(self, event):
        code, result = Utils.get_url(URL_WA, get_params={"i": event["args"],
            "appid": self.bot.config["wolframalpha-api-key"],
            "reinterpret": "true", "units": "metric"}, code=True)

        if not result == None:
            if code == 200:
                event["stdout"].write("%s: %s" % (event["args"], result))
            else:
                event["stdout"].write("No results")
        else:
            event["stderr"].write("Failed to load results")
