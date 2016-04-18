import gc, glob, imp, inspect, os, sys

class ModuleManager(object):
    def __init__(self, bot, directory="modules"):
        self.bot = bot
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
        import_name = "bitbot_%s" % name
        module = imp.load_source(import_name, filename)
        assert hasattr(module, "Module"
            ), "module '%s' doesn't have a Module class."
        assert inspect.isclass(module.Module
            ), "module '%s' has a Module attribute but it is not a class."
        module_object = module.Module(self.bot)
        if not hasattr(module_object, "_name"):
            module_object._name = name.title()
        module_object._is_unloaded = False
        module_object._import_name = import_name
        assert not module_object._name in self.modules, (
            "module name '%s' attempted to be used twice.")
        return module_object

    def load_module(self, filename):
        name = self.module_name(filename)
        module = self._load_module(filename)
        if module:
            self.modules[module._name] = module
            if name in self.waiting_requirement:
                for filename in self.waiting_requirement:
                    self.load_module(filename)
        else:
            sys.stderr.write("module '%s' not loaded.\n" % filename)
    def load_modules(self):
        for filename in self.list_modules():
            self.load_module(filename)

    def unload_module(self, module):
        # this is such a bad idea
        module._is_unloaded = True
        self.unhook_check(self.bot.events)
        if hasattr(module, "_cleanup"):
            module._cleanup()
        del sys.modules[module._import_name]
        del self.modules[module._name]
        del module
        gc.collect()

    def unhook_check(self, event):
        for hook in event.get_hooks():
            if hasattr(hook.function, "__self__") and hasattr(
                    hook.function.__self__, "_is_unloaded"
                    ) and hook.function.__self__._is_unloaded:
                event._unhook(hook)
        for child in event.get_children():
            self.unhook_check(event.get_child(child))
