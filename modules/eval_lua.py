#--depends-on commands

import socket
from src import ModuleManager, utils

EVAL_URL = "https://www.lua.org/cgi-bin/demo"

class Module(ModuleManager.BaseModule):
    _name = "Lua"
    @utils.hook("received.command.lua", min_args=1)
    def eval(self, event):
        try:
            page = utils.http.request(EVAL_URL, post_data=
                {"input": event["args"]}, method="POST")
        except socket.timeout:
            raise utils.EventError("%s: eval timed out" %
                event["user"].nickname)

        if page:
            textareas = page.soup().find_all("textarea")
            if len(textareas) > 1:
                out = textareas[1].text.strip("\n")
                event["stdout"].write("%s: %s" % (event["user"].nickname, out))
        else:
            event["stderr"].write("%s: failed to eval" % event["user"].nickname)
