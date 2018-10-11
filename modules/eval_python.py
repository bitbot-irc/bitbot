import socket
from src import ModuleManager, utils

EVAL_URL = "https://eval.appspot.com/eval"

class Module(ModuleManager.BaseModule):
    _name = "Python"
    @utils.hook("received.command.py", alias_of="python")
    @utils.hook("received.command.python", min_args=1)
    def eval(self, event):
        """
        :help: Evaluate a python statement
        :usage: <statement>
        """
        try:
            code, page = utils.http.get_url(EVAL_URL, get_params={
                "statement": event["args"]}, code=True)
        except socket.timeout:
            event["stderr"].write("%s: eval timed out" %
                event["user"].nickname)
            return

        if not page == None and code == 200:
            event["stdout"].write("%s: %s" % (event["user"].nickname,
                page))
        else:
            event["stderr"].write("%s: failed to eval" %
                event["user"].nickname)
