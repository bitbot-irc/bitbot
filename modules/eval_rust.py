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
    _name = "Rust"
    @utils.hook("received.command.rust", min_args=1)
    def eval(self, event):
        """
        :help: Evaluate a rust statement
        :usage: <statement>
        """
        args = API_ARGS.copy()
        args["code"] = FN_TEMPLATE % event["args"]
        try:
            page = utils.http.get_url(EVAL_URL, json_data=args,
                method="POST", json=True)
        except socket.timeout:
            event["stderr"].write("%s: eval timed out" %
                event["user"].nickname)
            return

        err_or_out = "stdout" if page["success"] else "stderr"
        event[err_or_out].write("%s: %s" % (event["user"].nickname,
            page[err_or_out].strip("\n")))
