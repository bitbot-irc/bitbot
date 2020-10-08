#--depends-on commands

from src import ModuleManager, utils
import re
import json

URL_WIKIPEDIA = "https://$lang.wikipedia.org/w/api.php"

@utils.export("channelset", utils.IntSetting("wikipedia-disambig-max",
    "Set the number disambiguation pages to show in a message"))

@utils.export("channelset", utils.Setting("wikipedia-lang",
    "Choose which language to use for Wikipedia",
    example="en"))

@utils.export("channelset", utils.BoolSetting("wikipedia-autolink",
    "Auto-translate to wiki-links"))


@utils.export("set", utils.Setting("wikipedia-lang",
    "Choose which language to use for Wikipedia",
    example="en"))

class Module(ModuleManager.BaseModule):
    def listify(self, items):
        if type(items) != list:
           items = list(items)
        
        return len(items) > 2 and ', '.join(items[:-1]) + ', or ' + items[-1] or len(items) > 1 and items[0] + ' or ' + items[1] or items and items[0] or ''

    def disambig(self, title, event):
        if not str(event["target"]).startswith('#'):
            api = utils.http.request(URL_WIKIPEDIA.replace('$lang', event["target"].get_setting("wikipedia-lang", "en")), get_params={
                "action": "parse", "format": "json", "page": title, "prop": "wikitext"}).json()
        else:
            api = utils.http.request(URL_WIKIPEDIA.replace('$lang', event["channel"].get_setting("wikipedia-lang", "en")), get_params={
                "action": "parse", "format": "json", "page": title, "prop": "wikitext"}).json()
        if api:
            text = api['parse']['wikitext']['*']
            links = []
            links.extend(re.findall('\* \[\[(.*)\]\]', text))
            links.extend(re.findall('\*\[\[(.*)\]\]', text))
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
            if len(disambigs) > event["channel"].get_setting("wikipedia-disambig-max", 10):
                return 'Sorry, but this page is too ambiguous. You may view the page at'
            else:
                return '%s could mean %s -' % (title, self.listify(disambigs))
    
    
    @utils.hook("received.message.channel")
    def handle_chanmsg(self, event):
        if not event["channel"].get_setting("wikipedia-autolink", False):
            return
        wikilink = re.search("\[\[(.*)\]\]", event["message"])
        if wikilink:
            page = wikilink.group(1)
        page = utils.http.request(URL_WIKIPEDIA.replace('$lang', event["channel"].get_setting("wikipedia-lang", "en")), get_params={
            "action": "query", "prop": "extracts|info", "inprop": "url",
            "titles": page, "exintro": "", "explaintext": "",
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
                    event["channel"].send_message("%s %s" % (self.disambig(title, event), url))
                else:
                    event["channel"].send_message("%s: %s - %s" % (title, info, url))
            else:
                event["channel"].send_message("No results found")
        else:
            raise utils.EventResultsError()
    
    
    @utils.hook("received.command.wi", alias_of="wiki")
    @utils.hook("received.command.wiki", alias_of="wikipedia")
    @utils.hook("received.command.wikipedia")
    @utils.kwarg("help", "Get information from wikipedia")
    @utils.spec("!<term>lstring")
    def wikipedia(self, event):
        if not str(event["target"]).startswith('#'):
            page = utils.http.request(URL_WIKIPEDIA.replace('$lang', event["target"].get_setting("wikipedia-lang", "en")), get_params={
                "action": "query", "prop": "extracts|info", "inprop": "url",
                "titles": event["spec"][0], "exintro": "", "explaintext": "",
                "exchars": "500", "redirects": "", "format": "json"}).json()
        else:
            page = utils.http.request(URL_WIKIPEDIA.replace('$lang', event["channel"].get_setting("wikipedia-lang", "en")), get_params={
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
                    event["stdout"].write("%s %s" % (self.disambig(title, event), url))
                else:
                    event["stdout"].write("%s: %s - %s" % (title, info, url))
            else:
                event["stderr"].write("No results found")
        else:
            raise utils.EventResultsError()
