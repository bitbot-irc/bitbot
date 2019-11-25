#--depends-on commands

import json, socket
from src import ModuleManager, utils

API_CRATE = "https://crates.io/api/v1/crates/%s"
URL_CRATE = "https://crates.io/crates/%s"

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
                method="POST", content_type="application/json").json()
        except socket.timeout:
            raise utils.EventError("%s: eval timed out" %
                event["user"].nickname)

        err_or_out = "stdout" if page["success"] else "stderr"
        event[err_or_out].write("%s: %s" % (event["user"].nickname,
            page[err_or_out].strip("\n")))

    @utils.hook("received.command.crate")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("help", "Look up a given Rust crate on crates.io")
    @utils.kwarg("usage", "<crate-name>")
    def crate(self, event):
        query = event["args_split"][0]
        request = utils.http.Request(API_CRATE % query)
        response = utils.http.request(request)
        if response.code == 200:
            crate = response.json()["crate"]
            name = crate["id"]
            url = URL_CRATE % name
            event["stdout"].write("%s %s: %s - %s" % (
                name, crate["max_version"], crate["description"], url))
        else:
            event["stderr"].write("Crate '%s' not found" % query)
