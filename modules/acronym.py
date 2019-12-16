from bitbot import ModuleManager, utils

API = "http://acronyms.silmaril.ie/cgi-bin/xaa?%s"

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.acronym")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("help", "Find possible acronym meanings")
    @utils.kwarg("usage", "<acronym>")
    def acronym(self, event):
        query = event["args_split"][0].upper()
        response = utils.http.request(API % query)

        acronyms = []
        for element in response.soup().find_all("acro"):
            acronyms.append(element.expan.string)

        if acronyms:
            event["stdout"].write("%s: %s" % (query, ", ".join(acronyms)))
        else:
            raise utils.EventResultsError()
