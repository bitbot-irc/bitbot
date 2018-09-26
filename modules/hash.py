import hashlib
from src import ModuleManager, Utils

class Module(ModuleManager.BaseModule):
    @Utils.hook("received.command.hash", min_args=2, usage="<algo> <string>")
    def hash(self, event):
        """
        Hash a given string with a given algorithm
        """
        algorithm = event["args_split"][0].lower()
        if algorithm in hashlib.algorithms_available:
            phrase = " ".join(event["args_split"][1:])
            cipher_text = hashlib.new(algorithm, phrase.encode("utf8")
                ).hexdigest()
            event["stdout"].write("%s -> %s" % (phrase, cipher_text))
        else:
            event["stderr"].write("Unknown algorithm provided")
