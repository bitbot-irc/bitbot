#--require-config wolframalpha-api-key
import json
from src import Utils

URL_WA = "https://api.wolframalpha.com/v1/result"

class Module(object):
    _name = "Wolfram|Alpha"
    def __init__(self, bot, events, exports):
        self.bot = bot

    @Utils.hook("received.command.wolframalpha|wa", min_args=1, usage="<query>")
    def wa(self, event):
        """
        Evauate a given string on Wolfram|Alpha
        """
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
