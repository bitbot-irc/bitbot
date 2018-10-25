import html, json, socket, urllib
from src import ModuleManager, utils


EVAL_URL = "https://tools.tutorialspoint.com/execute_new.php"
class Module(ModuleManager.BaseModule):
    _name = "PHP"

    def _evalphp(self, lang, event):
        page = None
        try:
            page = utils.http.get_url(EVAL_URL,
                post_data={
                    "lang": lang,
                    "code": event["args"],
                    "execute": "%s main.php" % lang,
                    "mainfile": "main.php",
                    "stdinput": event["args"]
                },
                method="POST")
        except:
            pass

        if page:
            out = {}
            out["out"] = page

            event["stdout"].write(out["out"].strip("\n"))
        else:
            event["stderr"].write("%s: failed to eval" % event["user"].nickname)

    @utils.hook("received.command.php", min_args=1)
    def chooselang(self, event):
        self._evalphp("php", event)
