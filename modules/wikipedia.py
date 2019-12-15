#--depends-on commands

from bitbot import ModuleManager, utils

URL_WIKIPEDIA = "https://en.wikipedia.org/w/api.php"

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.wi", alias_of="wiki")
    @utils.hook("received.command.wiki", alias_of="wikipedia")
    @utils.hook("received.command.wikipedia", min_args=1)
    def wikipedia(self, event):
        """
        :help: Get information from wikipedia
        :usage: <term>
        """
        page = utils.http.request(URL_WIKIPEDIA, get_params={
            "action": "query", "prop": "extracts|info", "inprop": "url",
            "titles": event["args"], "exintro": "", "explaintext": "",
            "exchars": "500", "redirects": "", "format": "json"}).json()

        if page:
            pages = page["query"]["pages"]
            article = list(pages.items())[0][1]
            if not "missing" in article:
                title, info = article["title"], article["extract"]
                title = article["title"]
                info = utils.parse.line_normalise(article["extract"])
                url = article["fullurl"]

                event["stdout"].write("%s: %s - %s" % (title, info, url))
            else:
                event["stderr"].write("No results found")
        else:
            raise utils.EventResultsError()

