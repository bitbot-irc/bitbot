import Utils

URL_HAVEIBEENPWNEDAPI = "https://haveibeenpwned.com/api/v2/breachedaccount/%s"
URL_HAVEIBEENPWNED = "https://haveibeenpwned.com/"

class Module(object):
    def __init__(self, bot, events, exports):
        events.on("received").on("command").on("beenpwned").hook(
            self.beenpwned, min_args=1,
            help="Find out if a username, email or similar has appeared "
            "in any hacked databases", usage="<username/email>")

    def beenpwned(self, event):
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
