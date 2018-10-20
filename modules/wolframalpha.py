#--require-config wolframalpha-api-key
import json
from src import ModuleManager, utils

URL_WA = "https://api.wolframalpha.com/v1/result"

class Module(ModuleManager.BaseModule):
    _name = "Wolfram|Alpha"

    @utils.hook("received.command.wa", alias_of="wolframalpha")
    @utils.hook("received.command.wolframalpha", min_args=1)
    def wa(self, event):
        """
        :help: Evauate a given string on Wolfram|Alpha
        :usage: <query>
        """
        code, result = utils.http.get_url(URL_WA,
            get_params={"i": event["args"],
            "appid": self.bot.config["wolframalpha-api-key"],
            "reinterpret": "true", "units": "metric"}, code=True)

        if not result == None:
            if code == 200:
                event["stdout"].write("%s: %s" % (event["args"], result))
            else:
                event["stdout"].write("No results")
        else:
            raise utils.EventsResultsError()
