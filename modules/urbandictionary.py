import json, re
from src import Utils

URL_URBANDICTIONARY = "http://api.urbandictionary.com/v0/define"
REGEX_DEFNUMBER = re.compile("-n(\d+) \S+")

class Module(object):
    def __init__(self, bot, events, exports):
        events.on("received.command").on("urbandictionary", "ud").hook(
            self.ud, min_args=1, help="Get the definition of a provided term",
            usage="<term>")

    def ud(self, event):
        term = event["args"]
        number = 1
        match = re.match(REGEX_DEFNUMBER, term)
        if match:
            number = int(match.group(1))
            term = term.split(" ", 1)[1]
        page = Utils.get_url(URL_URBANDICTIONARY, get_params={"term": term},
            json=True)
        if page:
            if len(page["list"]):
                if number > 0 and len(page["list"]) > number-1:
                    definition = page["list"][number-1]
                    event["stdout"].write("%s: %s" % (definition["word"],
                        definition["definition"].replace("\n", " ").replace(
                        "\r", "").replace("  ", " ")))
                else:
                    event["stderr"].write("Definition number does not exist")
            else:
                event["stderr"].write("No results found")
        else:
            event["stderr"].write("Failed to load results")
