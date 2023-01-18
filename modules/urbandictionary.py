#--depends-on commands

from src import ModuleManager, utils

URL_URBANDICTIONARY = "https://api.urbandictionary.com/v0/define"

class Module(ModuleManager.BaseModule):
    _name = "UrbanDictionary"

    @utils.hook("received.command.ud", alias_of="urbandictionary")
    @utils.hook("received.command.urbandictionary", min_args=1)
    def ud(self, event):
        """
        :help: Get the definition of a provided term from Urban Dictionary
        :usage: <term> [#<number>]
        """
        number = 1
        term = event["args_split"]
        if (event["args_split"][-1].startswith("#") and
                len(event["args_split"]) > 1 and
                event["args_split"][-1][1:].isdigit()):
            number = int(event["args_split"][-1][1:])
            term = term[:-1]
        term = " ".join(term)

        page = utils.http.request(URL_URBANDICTIONARY,
            get_params={"term": term}).json()
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
            raise utils.EventResultsError()
