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

    def _module_name(self, path):
        return os.path.basename(path).rsplit(".py", 1)[0].lower()
    def _module_path(self, name):
        return os.path.join(self.directory, "%s.py" % name)

    def _load_module(self, name):
        path = self._module_path(name)

        with open(path) as module_file:
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
                                self.waiting_requirement[line_split[1].lower()].add(path)
                            return None
                else:
                    break
        module = imp.load_source(name, path)

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

    def load_module(self, name):
        try:
            module = self._load_module(name)
        except ImportError as e:
            self.bot.log.error("failed to load module \"%s\": %s",
                [name, e.msg])
            return
        if module:
            self.modules[module._import_name] = module
            if name in self.waiting_requirement:
                for requirement_name in self.waiting_requirement:
                    self.load_module(requirement_name)
            self.bot.log.info("Module '%s' loaded", [name])
        else:
            self.bot.log.error("Module '%s' not loaded", [name])

    def load_modules(self, whitelist=None):
        for path in self.list_modules():
            name = self._module_name(path)
            if whitelist == None or name in whitelist:
                self.load_module(name)

    def unload_module(self, name):
        module = self.modules[name]
        del self.modules[name]

        event_context = module._event_context
        self.events.purge_context(event_context)

        del sys.modules[name]
        del module
