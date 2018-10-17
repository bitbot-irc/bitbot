import html, socket
from src import ModuleManager, utils

EVAL_TEMPLATE = """
import io, json, sys

compiled = compile(sys.stdin.read(), "code", "single")

old_stdout = sys.stdout
stdout = io.StringIO()
sys.stdout = stdout

try:
    result = eval(compiled)
except Exception as e:
    old_stdout.write(json.dumps({"success": False, "out": str(e)}))
    sys.exit()

stdout.write("\\n")
if not result == None:
    stdout.write(str(result)+"\\n")
old_stdout.write(json.dumps({"success": True, "out": stdout.getvalue()}))
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
            out = page.split("</b></span><br>", 1)[1].strip("\n")
            out = html.unescape(out)
            out = json.loads(out)

            event["stdout" if out["success"] else "stderr"].write(
                "%s: %s" % (event["user"].nickname, out))
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
