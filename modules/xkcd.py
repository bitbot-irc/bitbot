from src import ModuleManager, utils

URL_XKCD = "https://xkcd.com/"

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.x", alias_of="xkcd")
    @utils.hook("received.command.xkcd")
    def xkcd(self, event):
        """
        :help: Get given xkcd. Gets latest without a number
        :usage: [number]
        """
        query = "" or event["args"]
        if query:
            try: 
                int(query)
                xkcd_url = URL_XKCD + query
                page = utils.http.request(xkcd_url)
                if page:
                    title = page.soup().title.contents[0]
                    event["stdout"].write("xkcd: %s | url: %s" % (title, xkcd_url))
                else:
                    event["stderr"].write("Unable to fetch xkcd")
            except ValueError:
                event["stdout"].write("Please provide positive integer.")

