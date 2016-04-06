#--require-config bighugethesaurus-api-key

import Utils

URL_THESAURUS = "http://words.bighugelabs.com/api/2/%s/%s/json"

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("command").on("synonym",
            "antonym").hook(self.thesaurus, min_args=1,
            help="Get synonyms/antonyms for a provided phrase",
            usage="<word> [type]")

    def thesaurus(self, event):
        phrase = event["args_split"][0]
        page = Utils.get_url(URL_THESAURUS % (self.bot.config[
            "bighugethesaurus-api-key"], phrase), json=True)
        syn_ant = event["command"][:3]
        if page:
            if not len(event["args_split"]) > 1:
                word_types = []
                for word_type in page.keys():
                    if syn_ant in page[word_type]:
                        word_types.append(word_type)
                if word_types:
                    word_types = sorted(word_types)
                    event["stdout"].write(
                        "Available categories for %s: %s" % (
                        phrase, ", ".join(word_types)))
                else:
                    event["stderr"].write("No categories available")
            else:
                category = event["args_split"][1].lower()
                if category in page:
                    if syn_ant in page[category]:
                        event["stdout"].write("%ss for %s: %s" % (
                            event["command"].title(), phrase, ", ".join(
                            page[category][syn_ant])))
                    else:
                        event["stderr"].write("No %ss for %s" % (
                            event["command"], phrase))
                else:
                    event["stderr"].write("Category not found")
        else:
            event["stderr"].write("Failed to load results")
