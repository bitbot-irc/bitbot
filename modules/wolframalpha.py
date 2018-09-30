#--require-config wolframalpha-api-key
import json
from src import ModuleManager, Utils

URL_WA = "https://api.wolframalpha.com/v1/result"

class Module(ModuleManager.BaseModule):
    _name = "Wolfram|Alpha"

    @Utils.hook("received.command.wolframalpha|wa", min_args=1)
    def wa(self, event):
        """
        :help: Evauate a given string on Wolfram|Alpha
        :usage: <query>
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
