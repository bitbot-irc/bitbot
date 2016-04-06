#--require-config wolframalpha-api-key

import re
import Utils

URL_WA = "http://api.wolframalpha.com/v2/query"
REGEX_CHARHEX = re.compile("\\\\:(\S{4})")

class Module(object):
    _name = "Wolfram|Alpha"
    def __init__(self, bot):
        bot.events.on("received").on("command").on("wolframalpha", "wa"
            ).hook(self.wa, min_args=1, help=
            "Evauate a given string on Wolfram|Alpha",
            usage="<query>")
        self.bot = bot

    def wa(self, event):
        soup = Utils.get_url(URL_WA, get_params={"input": event["args"],
            "appid": self.bot.config["wolframalpha-api-key"],
            "format": "plaintext", "reinterpret": "true"}, soup=True)

        if soup:
            if int(soup.find("queryresult").get("numpods")) > 0:
                input = soup.find(id="Input").find("subpod").find("plaintext"
                    ).text
                answered = False
                for pod in soup.find_all("pod"):
                    if pod.get("primary") == "true":
                        answer = pod.find("subpod").find("plaintext")
                        text = "(%s) %s" % (input.replace(" | ", ": "),
                            answer.text.strip().replace(" | ", ": "
                            ).replace("\n", " | ").replace("\r", ""))
                        while True:
                            match = re.search(REGEX_CHARHEX, text)
                            if match:
                                text = re.sub(REGEX_CHARHEX, chr(int(
                                    match.group(1), 16)), text)
                            else:
                                break
                        answered = True
                        event["stdout"].write(text)
                        break
                if not answered:
                    event["stderr"].write("No results found")
            else:
                event["stderr"].write("No results found")
        else:
            event["stderr"].write("Failed to load results")
