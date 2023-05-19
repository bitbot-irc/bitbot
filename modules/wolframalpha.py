#--depends-on commands
#--require-config wolframalpha-api-key

import json
from src import ModuleManager, utils

URL_WA = "https://api.wolframalpha.com/v2/query"

class Module(ModuleManager.BaseModule):
    _name = "Wolfram|Alpha"

    @utils.hook("received.command.wa", alias_of="wolframalpha")
    @utils.hook("received.command.wolframalpha", min_args=1)
    def wa(self, event):
        """
        :help: Evaluate a given string on Wolfram|Alpha
        :usage: <query>
        """
        query = event["args"].strip()
        try:
            page = utils.http.request(URL_WA, timeout=10, get_params={
                "input": query, "format": "plaintext",
                "output": "JSON", "reinterpret": "true", "units": "metric",
                "appid": self.bot.config["wolframalpha-api-key"]}).json()
        except utils.http.HTTPTimeoutException:
            page = None

        if page:
            if page["queryresult"]["numpods"]:
                input = query
                primaries = []
                for pod in page["queryresult"]["pods"]:
                    text = pod["subpods"][0]["plaintext"]
                    if pod["id"] == "Input" and text:
                        input = text.replace("\n", " | ")
                    elif pod.get("primary", False):
                        primaries.append(text)

                event["stdout"].write("%s: %s" % (input, " | ".join(primaries)))
            else:
                event["stdout"].write("No results")
        else:
            raise utils.EventResultsError()
