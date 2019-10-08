import socket
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

    @utils.hook("received.command.isupraw")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("help", "Check if a given hostname:port is up or not")
    @utils.kwarg("usage", "<hostname>[:port]")
    def isupraw(self, event):
        hostname, _, port = event["args_split"][0].partition(":")
        port = utils.parse.try_int(port or "80")
        if port == None:
            raise utils.EventError("Port must be a number")

        error = None
        try:
            with utils.deadline(seconds=5):
                socket.create_connection((hostname, port))
        except utils.DeadlineExceededException:
            error = "timed out"
        except Exception as e:
            error = str(e)

        if error == None:
            event["stdout"].write("%s:%d looks up to me" % (hostname, port))
        else:
            event["stderr"].write("%s:%d looks down to me (%s)" %
                (hostname, port, error))

