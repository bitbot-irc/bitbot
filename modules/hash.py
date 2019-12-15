#--depends-on commands

import hashlib
from bitbot import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.hash", remove_empty=False)
    def hash(self, event):
        """
        :help: Hash a given string with a given algorithm
        :usage: <algo> <string>
        """
        if event["args_split"]:
            algorithm = event["args_split"][0].lower()
            phrase = " ".join(event["args_split"][1:])
            if algorithm in hashlib.algorithms_available:
                cipher_text = hashlib.new(algorithm, phrase.encode("utf8")
                    ).hexdigest()
                event["stdout"].write("%s -> %s" % (phrase, cipher_text))
            else:
                event["stderr"].write("Unknown algorithm provided")
        else:
            event["stdout"].write("Available algorithms: %s" %
                ", ".join(hashlib.algorithms_available))
