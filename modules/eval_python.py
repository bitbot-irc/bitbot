import socket
from src import ModuleManager, utils

EVAL_TEMPLATE = """
import sys
compiled = compile(sys.stdin.read(), "code", "single")
result = eval(compiled)
print("")
if not result == None:
    sys.stdout.write(str(result))
"""

EVAL_URL = "https://tpcg.tutorialspoint.com/tpcg.php"
class Module(ModuleManager.BaseModule):
    _name = "Python"

    def _eval(self, lang, event):
        try:
            page = utils.http.get_url(EVAL_URL,
                post_data={
                    "lang": lang,
                    "code": EVAL_TEMPLATE,
                    "execute": "%s main.py" % lang,
                    "mainfile": "main.py",
                    "stdinput": event["args"]
                },
                method="POST")
        except:
            pass

        if page:
            event["stdout"].write("%s: %s" % (event["user"].nickname,
                page.split("</b></span><br>", 1)[1].strip("\n")))
        else:
            event["stderr"].write("%s: failed to eval" % event["user"].nickname)

    @utils.hook("received.command.py2", alias_of="python2")
    @utils.hook("received.command.python2", min_args=1)
    def eval(self, event):
        self._eval("python", event)

    @utils.hook("received.command.py", alias_of="python")
    @utils.hook("received.command.py3", alias_of="python")
    @utils.hook("received.command.python", alias_of="python3")
    @utils.hook("received.command.python3", min_args=1)
    def eval3(self, event):
        self._eval("python3", event)
