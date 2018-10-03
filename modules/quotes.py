import random, time
from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    def category_and_quote(self, s):
        if "=" in s:
            return [part.strip() for part in s.split("=", 1)]
        return None, None

    @utils.hook("received.command.quoteadd|qadd", min_args=1)
    def quote_add(self, event):
        """
        :help: Add a quote to a category
        :usage: <category> = <quote>
        """
        category, quote = self.category_and_quote(event["args"])
        if category and quote:
            setting = "quotes-%s" % category
            quotes = event["server"].get_setting(setting, [])
            quotes.append([event["user"].name, int(time.time()), quote])
            event["server"].set_setting(setting, quotes)
            event["stdout"].write("Quote added")
        else:
            event["stderr"].write("Please provide a category AND quote")

    @utils.hook("received.command.quoteget|qget", min_args=1)
    def quote_get(self, event):
        """
        :help: Get a quote from a ccategory
        :usage: <category> = <search>
        """
        category, to_find = self.category_and_quote(event["args"])
        if category and to_find:
            to_find = to_find.lower()
            quotes = event["server"].get_setting("quotes-%s" % category, [])
            found = []
            for nickname, time_added, quote in quotes:
                if to_find in quote.lower():
                    found.append(quote)
            if found:
                event["stdout"].write("%d quote%s found: %s" % (len(found),
                    "s" if len(found) > 1 else "", found[0]))
            else:
                event["stderr"].write("No quotes found")
        else:
            event["stderr"].write("Please provide a category and a "
                "part of a quote to find")

    @utils.hook("received.command.quotedel|qdel", min_args=1)
    def quote_del(self, event):
        """
        :help: Delete a quote from a category
        :usage: <category> = <quote>
        """
        category, remove_quote = self.category_and_quote(event["args"])
        remove_quote_lower = remove_quote.lower()
        if category and remove_quote:
            setting = "quotes-%s" % category
            quotes = event["server"].get_setting(setting, [])
            removed = False
            for nickname, time_added, quote in quotes[:]:
                if quote.lower() == remove_quote_lower:
                    quotes.remove([nickname, time_added, quote])
                    removed = True
            if removed:
                event["server"].set_setting(setting, quotes)
                event["stdout"].write("Removed quote")
            else:
                event["stderr"].write("Quote not found")
        else:
            event["stderr"].write("Please provide a category and a quote "
                "to remove")

    @utils.hook("received.command.quote|q", min_args=1)
    def quote(self, event):
        """
        :help: Get a random quote from a category
        :usage: <category>
        """
        category = event["args"].strip().lower()
        quotes = event["server"].get_setting("quotes-%s" % category, [])
        if quotes:
            index = random.randint(0, len(quotes)-1)
            nickname, time_added, quote = quotes[index]
            event["stdout"].write("%s: %s" % (category, quote))
        else:
            event["stderr"].write("There are no quotes for this category")
