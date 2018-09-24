import socket
from src import Utils

EVAL_URL = "https://eval.appspot.com/eval"

class Module(object):
    def __init__(self, bot, events, exports):
        events.on("received.command.eval").hook(self.eval, min_args=1,
            help="Evaluate a python statement", usage="<statement>")

    def eval(self, event):
        try:
            code, page = Utils.get_url(EVAL_URL, get_params={
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
