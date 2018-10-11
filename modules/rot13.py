import codecs
from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.rot13")
    def rot13(self, event):
        line = event["args"] or event["target"].buffer.get().message
        event["stdout"].write("%s: %s" % (event["user"].nickname,
            codecs.encode(line, "rot_13")))
