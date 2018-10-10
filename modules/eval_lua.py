import socket
from src import ModuleManager, utils

EVAL_URL = "https://www.lua.org/cgi-bin/demo"

class Module(ModuleManager.BaseModule):
    _name = "Lua"
    @utils.hook("received.command.lua", min_args=1)
    def eval(self, event):
        try:
            page = utils.http.get_url(EVAL_URL,
                post_params={"input": event["args"]},
                method="POST",
                soup=True)
        except socket.timeout:
            event["stderr"].write("%s: eval timed out" %
                event["user"].nickname)
            return

        if page:
            textareas = page.find_all("textarea")
            if len(textareas) > 1:
                out = textareas[1].text.strip("\n")
                event["stdout"].write("%s: %s" % (event["user"].nickname, out))
        else:
            event["stderr"].write("%s: failed to eval" % event["user"].nickname)
