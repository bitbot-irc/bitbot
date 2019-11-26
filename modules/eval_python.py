#--depends-on commands

import urllib.parse
from src import ModuleManager, utils

EVAL_URL = "http://dotpy3.herokuapp.com/"

class Module(ModuleManager.BaseModule):
    _name = "Python"

    @utils.hook("received.command.py", alias_of="python")
    @utils.hook("received.command.python")
    def _eval(self, event):
        url = "%s?%s" % (EVAL_URL, urllib.parse.quote(event["args"]))

        page = None
        try:
            page = utils.http.request(url)
        except:
            pass

        if page and page.data:
            event["stdout"].write("%s: %s" % (event["user"].nickname,
                page.decode().rstrip("\n")))
        else:
            event["stderr"].write("%s: failed to eval" % event["user"].nickname)
