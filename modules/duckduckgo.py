#--depends-on commands

from bitbot import ModuleManager, utils

URL_DDG = "https://api.duckduckgo.com"

class Module(ModuleManager.BaseModule):
    _name = "DDG"

    @utils.hook("received.command.ddg", min_args=1)
    def duckduckgo(self, event):
        """
        :help: Get first DuckDuckGo result for a given search term
        :usage: [search term]
        """

        phrase = event["args"] or event["target"].buffer.get()
        if phrase:
            page = utils.http.request(URL_DDG, get_params={
                "q": phrase, "format": "json", "no_html": "1",
                "no_redirect": "1"}).json()

            if page and page["AbstractURL"]:
                event["stdout"].write(page["AbstractURL"])
            else:
                event["stderr"].write("No results found")
