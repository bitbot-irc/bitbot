from src import ModuleManager, Utils

URL_HAVEIBEENPWNEDAPI = "https://haveibeenpwned.com/api/v2/breachedaccount/%s"
URL_HAVEIBEENPWNED = "https://haveibeenpwned.com/"

class Module(ModuleManager.BaseModule):
    @Utils.hook("received.command.beenpwned", usage="<username/email>",
        min_args=1)
    def beenpwned(self, event):
        """
        Find out if a username, email or similar has appeared in any
        hacked databases
        """
        page = Utils.get_url(URL_HAVEIBEENPWNEDAPI % event["args"], json=True,
            code=True)
        if page:
            code, page = page
            if code == 200:
                event["stdout"].write(
                    "It seems '%s' has been pwned. check on %s." % (event["args"],
                    URL_HAVEIBEENPWNED))
            else:
                event["stdout"].write("It seems '%s' has not been pwned" % (
                    event["args"]))
        else:
            event["stderr"].write("Failed to load results")
