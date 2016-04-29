import time

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("command").on("quoteadd",
            "qadd").hook(self.quote_add, min_args=1,
            help="Added a quote to a category",
            usage="<category> = <quote>")
        bot.events.on("received").on("command").on("quoteget",
            "qget").hook(self.quote_get, min_args=1,
            help="Find a quote within a category",
            usage="<category> = <search>")
        bot.events.on("received").on("command").on("quotedel",
            "qdel").hook(self.quote_del, min_args=1,
            help="Delete a quote from a category",
            usage="<category> = <quote>")

    def category_and_quote(self, s):
        if "=" in s:
            return [part.strip() for part in s.split("=", 1)]
        return None, None

    def quote_add(self, event):
        category, quote = self.category_and_quote(event["args"])
        if category and quote:
            setting = "quotes-%s" % category
            quotes = event["server"].get_setting(setting, [])
            quotes.append([event["user"].name, time.time(), quote])
            event["server"].set_setting(setting, quotes)
            event["stdout"].write("Quote added")
        else:
            event["stderr"].write("Please provide a category AND quote")

    def quote_get(self, event):
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

    def quote_del(self, event):
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
