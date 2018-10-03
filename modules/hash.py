import hashlib
from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.hash", min_args=2)
    def hash(self, event):
        """
        :help: Hash a given string with a given algorithm
        :usage: <algo> <string>
        """
        algorithm = event["args_split"][0].lower()
        if algorithm in hashlib.algorithms_available:
            phrase = " ".join(event["args_split"][1:])
            cipher_text = hashlib.new(algorithm, phrase.encode("utf8")
                ).hexdigest()
            event["stdout"].write("%s -> %s" % (phrase, cipher_text))
        else:
            event["stderr"].write("Unknown algorithm provided")
