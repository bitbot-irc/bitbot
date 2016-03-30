import glob, imp, inspect, os, sys

class ModuleManager(object):
    def __init__(self, bot, directory="modules"):
        self.bot = bot
        self.directory = directory
        self.modules = {}
    def list_modules(self):
        return sorted(glob.glob(os.path.join(self.directory, "*.py")))
    def load_module(self, filename):
        name = os.path.basename(filename).rsplit(".py", 1)[0]
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
                        if not line_split[1].lower() in self.bot.config:
                            # nope, required config option not present.
                            return None
                else:
                    break
        module = imp.load_source("bitbot_%s" % name, filename)
        assert hasattr(module, "Module"
            ), "module '%s' doesn't have a Module class."
        assert inspect.isclass(module.Module
            ), "module '%s' has a Module attribute but it is not a class."
        module_object = module.Module(self.bot)
        if not hasattr(module_object, "_name"):
            module_object._name = name.title()
        return module_object
    def load_modules(self):
        for filename in self.list_modules():
            module = self.load_module(filename)
            if module:
                assert not module._name in self.modules, (
                    "module name '%s' attempted to be used twice.")
                self.modules[module._name] = module
            else:
                sys.stderr.write("module '%s' not loaded.\n" % filename)
