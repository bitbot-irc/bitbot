
import glob, os, subprocess
from src import Utils

class Module(object):
    def __init__(self, bot, events, exports):
        self.events = events
        self._directory = os.path.join(bot.directory, "modules", "scripts")
        self.read()

    def read(self):
        for filename in glob.glob(os.path.join(self._directory, "*")):
            name = os.path.basename(filename)
            for hashflag, value in Utils.get_hashflags(filename):
                if hashflag == "name" and value:
                    name = value
                elif hashflag == "hook" and value:
                    self.events.on(value).hook(
                        lambda x: self.call(x, filename, name))

    def call(self, event, filename, name):
        env = {}
        env["EVENT"] = event.name
        for key, value in event.kwargs.items():
            env[key.upper()] = str(value)

        proc = subprocess.Popen([filename], stdout=subprocess.PIPE, env=env)
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            # execution of script expired
            return

        out = proc.stdout.read().decode("utf8").strip("\n")
        if out:
            if proc.returncode == 0:
                if "stdout" in event:
                    event["stdout"].set_prefix(name)
                    event["stdout"].write(out)
            else:
                if "stderr" in event:
                    event["stderr"].set_prefix(name)
                    event["stderr"].write(out)
