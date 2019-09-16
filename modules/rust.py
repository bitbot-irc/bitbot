#--depends-on commands

import json, socket
from src import ModuleManager, utils

EVAL_URL = "https://play.rust-lang.org/execute"
FN_TEMPLATE = """
fn main() {
    println!("{:?}", {
        %s
    });
}
"""
API_ARGS = {
    "channel": "nightly",
    "crateType": "bin",
    "mode": "debug",
    "tests": False,
    "execute": True,
    "target": "ast",
    "backtrace": False
}

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.rust", min_args=1)
    def eval(self, event):
        """
        :help: Evaluate a rust statement
        :usage: <statement>
        """
        args = API_ARGS.copy()
        args["code"] = FN_TEMPLATE % event["args"]
        try:
            page = utils.http.request(EVAL_URL, post_data=args,
                method="POST", json=True, content_type="application/json")
        except socket.timeout:
            raise utils.EventError("%s: eval timed out" %
                event["user"].nickname)

        err_or_out = "stdout" if page.data["success"] else "stderr"
        event[err_or_out].write("%s: %s" % (event["user"].nickname,
            page.data[err_or_out].strip("\n")))
