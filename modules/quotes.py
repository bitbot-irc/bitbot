#--depends-on commands

import random, time
from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def category_and_quote(self, s):
        if "=" in s:
            return [part.strip() for part in s.split("=", 1)]
        return None, None

    def _get_quotes(self, server, category):
        return server.get_setting("quotes-%s" % category, [])
    def _set_quotes(self, server, category, quotes):
        server.set_setting("quotes-%s" % category, quotes)

    @utils.hook("received.command.qadd", alias_of="quoteadd")
    @utils.hook("received.command.quoteadd", min_args=1)
    def quote_add(self, event):
        """
        :help: Add a quote to a category
        :usage: <category> = <quote>
        """
        category, quote = self.category_and_quote(event["args"])
        if category and quote:
            quotes = self._get_quotes(event["server"], category)
            quotes.append([event["user"].name, int(time.time()), quote])
            self._set_quotes(event["server"], category, quotes)
            event["stdout"].write("Quote added")
        else:
            event["stderr"].write("Please provide a category AND quote")

    @utils.hook("received.command.qdel", alias_of="quotedel")
    @utils.hook("received.command.quotedel", min_args=1)
    def quote_del(self, event):
        """
        :help: Delete a quote from a category
        :usage: <category> = <quote>
        """
        category, remove_quote = self.category_and_quote(event["args"])
        category = category or event["args"].strip()

        message = None
        setting = "quotes-%s" % category
        quotes = event["server"].get_setting(setting, [])

        if not quotes:
            raise utils.EventError("Quote category '%s' not found" %
                category)

        if not remove_quote == None:
            remove_quote_lower = remove_quote.lower()
            for nickname, time_added, quote in quotes[:]:
                if quote.lower() == remove_quote_lower:
                    quotes.remove([nickname, time_added, quote])
                    message = "Removed quote from '%s'"
                    break
        else:
            if quotes:
                quotes.pop(-1)
                message = "Removed last '%s' quote"

        if not message == None:
            event["server"].set_setting(setting, quotes)
            event["stdout"].write(message % category)
        else:
            event["stderr"].write("Quote not found")

    @utils.hook("received.command.q", alias_of="quote")
    @utils.hook("received.command.quote", min_args=1)
    def quote(self, event):
        """
        :help: Get a random quote from a category
        :usage: <category>
        """
        category, search = self.category_and_quote(event["args"])
        quotes = event["server"].get_setting("quotes-%s" % category, [])
        if search:
            search_lower = search.lower()
            quotes = [q for q in quotes if search_lower in q[-1].lower()]

        if quotes:
            index = random.randint(0, len(quotes)-1)
            nickname, time_added, quote = quotes[index]

            category_str = category
            if search:
                category_str = "%s (%s [%d found])" % (category_str, search,
                    len(quotes))
            event["stdout"].write("%s: %s" % (category_str, quote))
        else:
            event["stderr"].write("No matching quotes")

    @utils.hook("received.command.grab", alias_of="quotegrab")
    @utils.hook("received.command.quotegrab", min_args=1, channel_only=True)
    def quote_grab(self, event):
        line = event["target"].buffer.find_from(event["args_split"][0])
        if line:
            quotes = self._get_quotes(event["server"], line.sender)
            text = None
            if line.action:
                text = "* %s %s" % (line.sender, line.message)
            else:
                text = "<%s> %s" % (line.sender, line.message)
            quotes.append([event["user"].name, int(time.time()), text])
            self._set_quotes(event["server"], line.sender, quotes)
            event["stdout"].write("Quote added")
        else:
            event["stderr"].write("Nothing found to quote")
