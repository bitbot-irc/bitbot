#--depends-on commands
#--require-config bighugethesaurus-api-key

from src import ModuleManager, utils

URL_THESAURUS = "http://words.bighugelabs.com/api/2/%s/%s/json"

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.synonym", min_args=1)
    @utils.hook("received.command.antonym", min_args=1)
    def thesaurus(self, event):
        """
        :help: Get synonyms/antonyms for a provided phrase
        :usage: <word> [type]
        """
        phrase = event["args_split"][0]
        page = utils.http.request(URL_THESAURUS % (
            self.bot.config["bighugethesaurus-api-key"], phrase))
        syn_ant = event["command"][:3]
        if page:
            if page.code == 404:
                raise utils.EventError("Word not found")
            page = page.json()

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
            raise utils.EventResultsError()
