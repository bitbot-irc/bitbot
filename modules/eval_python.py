import socket
from src import ModuleManager, utils

EVAL_URL = "https://pyeval.appspot.com/exec"

class Module(ModuleManager.BaseModule):
    _name = "Python"
    @utils.hook("received.command.py", alias_of="python")
    @utils.hook("received.command.python", min_args=1)
    def eval(self, event):
        """
        :help: Evaluate a python statement
        :usage: <statement>
        """
        id = None
        try:
            id = utils.http.get_url(EVAL_URL,
                post_data={"input": event["args"]},
                method="POST")
        except:
            pass

        if not id == None:
            try:
                page = utils.http.get_url(EVAL_URL,
                    get_params={"id": id},
                    json=True)
            except socket.timeout:
                event["stderr"].write("%s: eval timed out" %
                    event["user"].nickname)
                return

            if page:
                event["stdout"].write("%s: %s" % (event["user"].nickname,
                    page["output"].strip("\n")))
                return

        event["stderr"].write("%s: failed to eval" % event["user"].nickname)
