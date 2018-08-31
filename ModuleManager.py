import gc, glob, imp, inspect, os, sys, uuid

class ModuleManager(object):
    def __init__(self, bot, events, directory="modules"):
        self.bot = bot
        self.events = events
        self.directory = directory
        self.modules = {}
        self.waiting_requirement = {}
    def list_modules(self):
        return sorted(glob.glob(os.path.join(self.directory, "*.py")))

    def module_name(self, filename):
        return os.path.basename(filename).rsplit(".py", 1)[0].lower()

    def _load_module(self, filename):
        name = self.module_name(filename)

        with open(filename) as module_file:
            while True:
                line = module_file.readline().strip()
                line_split = line.split(" ")
                if line and line.startswith("#--"):
                    # this is a hashflag
                    if line == "#--ignore":
                        # nope, ignore this module.
                        return None
                    elif line_split[0] == "#--require-config" and len(
                            line_split) > 1:
                        if not line_split[1].lower() in self.bot.config or not self.bot.config[
                                    line_split[1].lower()]:
                            # nope, required config option not present.
                            return None
                    elif line_split[0] == "#--require-module" and len(
                            line_split) > 1:
                        if not "bitbot_%s" % line_split[1].lower() in sys.modules:
                            if not line_split[1].lower() in self.waiting_requirement:
                                self.waiting_requirement[line_split[1].lower()] = set([])
                            self.waiting_requirement[line_split[1].lower()].add(filename)
                            return None
                else:
                    break
        module = imp.load_source(name, filename)

        if not hasattr(module, "Module"):
            raise ImportError("module '%s' doesn't have a Module class.")
        if not inspect.isclass(module.Module):
            raise ImportError("module '%s' has a Module attribute but it is not a class.")

        event_context = uuid.uuid4()
        module_object = module.Module(self.bot, self.events.new_context(
            event_context))
        if not hasattr(module_object, "_name"):
            module_object._name = name.title()
        module_object._event_context = event_context
        module_object._is_unloaded = False
        module_object._import_name = name

        assert not module_object._name in self.modules, (
            "module name '%s' attempted to be used twice.")
        return module_object

    def load_module(self, filename):
        name = self.module_name(filename)
        try:
            module = self._load_module(filename)
        except ImportError as e:
            sys.stderr.write("module '%s' not loaded: Could not resolve import.\n" % filename)
            return
        if module:
            self.modules[module._import_name] = module
            if name in self.waiting_requirement:
                for filename in self.waiting_requirement:
                    self.load_module(filename)
            sys.stderr.write("module '%s' loaded.\n" % filename)
        else:
            sys.stderr.write("module '%s' not loaded.\n" % filename)

    def load_modules(self, whitelist=None):
        for filename in self.list_modules():
            if whitelist == None or filename in whitelist:
                self.load_module(filename)
