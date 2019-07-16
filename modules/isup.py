from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    _name = "isup"

    @utils.hook("received.command.isup")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("help", "Check if a given URL is up or not")
    @utils.kwarg("usage", "<url>")
    def isup(self, event):
        url = event["args_split"][0]

        response = None
        try:
            response = utils.http.request(url)
        except:
            raise utils.EventError("%s looks down to me" % url)

        event["stdout"].write("%s looks up to me (HTTP %d)" %
            (url, response.code))
