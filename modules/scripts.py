
import glob, json, os, subprocess
from src import IRCObject, Utils

class Module(object):
    def __init__(self, bot, events, exports):
        self.events = events
        self._directory = os.path.join(bot.directory, "modules", "scripts")
        self._hooks = []
        self._load_scripts()

    def _load_scripts(self):
        for filename in glob.glob(os.path.join(self._directory, "*")):
            name = os.path.basename(filename)
            for hashflag, value in Utils.get_hashflags(filename):
                if hashflag == "name" and value:
                    name = value
                elif hashflag == "hook" and value:
                    hook = self.events.on(value).hook(
                        lambda x: self.call(x, filename, name))
                    self._hooks.append([value, hook])

    @Utils.hook("received.command.reloadscripts", permission="reloadscripts")
    def reload(self, event):
        for event_name, hook in self._hooks:
            self.events.on(event_name).unhook(hook)
        self._load_scripts()
        event["stdout"].write("Reloaded all scripts")

    def call(self, event, filename, name):
        env = {}
        env["EVENT"] = event.name
        for key, value in event.kwargs.items():
            if isinstance(value, (str,)):
                env[key.upper()] = value
            elif isinstance(value, (bool,)):
                env[key.upper()] = str(int(value))
            elif isinstance(value, (list, dict)):
                env[key.upper()] = json.dumps(value)
            elif isinstance(value, (IRCObject.Object,)):
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
