from src import ModuleManager, utils

URL_HAVEIBEENPWNEDAPI = "https://haveibeenpwned.com/api/v2/breachedaccount/%s"
URL_HAVEIBEENPWNED = "https://haveibeenpwned.com/"

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.beenpwned", min_args=1)
    def beenpwned(self, event):
        """
        :help: Find out if a username, email or similar has appeared in any
            hacked databases
        :usage: <username/email>
        """
        page = utils.http.request(URL_HAVEIBEENPWNEDAPI % event["args"],
            json=True, code=True)
        if page:
            if page.code == 200:
                event["stdout"].write(
                    "It seems '%s' has been pwned. check on %s." % (event["args"],
                    URL_HAVEIBEENPWNED))
            else:
                event["stdout"].write("It seems '%s' has not been pwned" % (
                    event["args"]))
        else:
            raise utils.EventsResultsError()
