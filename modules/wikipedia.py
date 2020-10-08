#--depends-on commands

from src import ModuleManager, utils
import re
import json

URL_WIKIPEDIA = "https://en.wikipedia.org/w/api.php"

class Module(ModuleManager.BaseModule):
    def listify(self, items):
        if type(items) != list:
           items = list(items)
        return len(items) > 1 and ', '.join(items[:-1]) + ', or ' + items[-1] or items and items[0] or ''

    def disambig(self, title):
        api = utils.http.request(URL_WIKIPEDIA, get_params={
            "action": "parse", "format": "json", "page": title, "prop": "wikitext"}).json()
        if api:
            text = api['parse']['wikitext']['*']
            links = re.findall('\* \[\[(.*)\]\]', text)
            disambigs = []
            if links:
                for link in links:
                    # parse through the wikitext adventure
                    if '|' in link:
                        d = link.split('|')[1]
                    else:
                        d = link
                    d = d.replace('\'', '').replace('\'', '').replace('"', '')
                    disambigs.append(d)
            else:
                return 'Unable to parse disambiguation page. You may view the page at'
            if len(disambigs) > 15:
                return 'Sorry, but this page is too ambiguous. You may view the page at'
            else:
                return '%s could mean %s -' % (title, self.listify(disambigs))
    @utils.hook("received.command.wi", alias_of="wiki")
    @utils.hook("received.command.wiki", alias_of="wikipedia")
    @utils.hook("received.command.wikipedia")
    @utils.kwarg("help", "Get information from wikipedia")
    @utils.spec("!<term>lstring")
    def wikipedia(self, event):
        page = utils.http.request(URL_WIKIPEDIA, get_params={
            "action": "query", "prop": "extracts|info", "inprop": "url",
            "titles": event["spec"][0], "exintro": "", "explaintext": "",
            "exchars": "500", "redirects": "", "format": "json"}).json()

        if page:
            pages = page["query"]["pages"]
            article = list(pages.items())[0][1]
            if not "missing" in article:
                title, info = article["title"], article["extract"]
                title = article["title"]
                info = utils.parse.line_normalise(article["extract"])
                url = article["fullurl"]
                if 'may refer to' in info:
                    event["stdout"].write("%s %s" % (self.disambig(title), url))
                else:
                    event["stdout"].write("%s: %s - %s" % (title, info, url))
            else:
                event["stderr"].write("No results found")
        else:
            raise utils.EventResultsError()
