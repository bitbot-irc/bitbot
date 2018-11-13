import gc, glob, imp, io, inspect, os, sys, typing, uuid
from src import Config, EventManager, Exports, IRCBot, Logging, Timers, utils

class ModuleException(Exception):
    pass
class ModuleWarning(Exception):
    pass

class ModuleNotFoundException(ModuleException):
    pass
class ModuleNameCollisionException(ModuleException):
    pass
class ModuleLoadException(ModuleException):
    pass
class ModuleUnloadException(ModuleException):
    pass

class ModuleNotLoadedWarning(ModuleWarning):
    pass

class BaseModule(object):
    def __init__(self,
            bot: "IRCBot.Bot",
            events: EventManager.EventHook,
            exports: Exports.Exports,
            timers: Timers.Timers,
            log: Logging.Log):
        self.bot = bot
        self.events = events
        self.exports = exports
        self.timers = timers
        self.log = log
        self.on_load()
    def on_load(self):
        pass

class ModuleManager(object):
    def __init__(self,
            events: EventManager.EventHook,
            exports: Exports.Exports,
            timers: Timers.Timers,
            config: Config.Config,
            log: Logging.Log,
            directory: str):
        self.events = events
        self.exports = exports
        self.config = config
        self.timers = timers
        self.log = log
        self.directory = directory

        self.modules = {}
        self.waiting_requirement = {}

    def list_modules(self) -> typing.List[str]:
        return sorted(glob.glob(os.path.join(self.directory, "*.py")))

    def _module_name(self, path: str) -> str:
        return os.path.basename(path).rsplit(".py", 1)[0].lower()
    def _module_path(self, name: str) -> str:
        return os.path.join(self.directory, "%s.py" % name)
    def _import_name(self, name: str) -> str:
        return "bitbot_%s" % name

    def _get_magic(self, obj: typing.Any, magic: str, default: typing.Any
            ) -> typing.Any:
        return getattr(obj, magic) if hasattr(obj, magic) else default

    def _load_module(self, bot: "IRCBot.Bot", name: str):
        path = self._module_path(name)

        for hashflag, value in utils.parse.hashflags(path):
            if hashflag == "ignore":
               # nope, ignore this module.
               raise ModuleNotLoadedWarning("module ignored")

            elif hashflag == "require-config" and value:
                if not self.config.get(value.lower(), None):
                    # nope, required config option not present.
                    raise ModuleNotLoadedWarning("required config not present")

            elif hashflag == "require-module" and value:
                requirement = value.lower()
                if not requirement in self.modules:
                    if not requirement in self.waiting_requirement:
                        self.waiting_requirement[requirement] = set([])
                        self.waiting_requirement[requirement].add(path)
                    raise ModuleNotLoadedWarning("waiting for requirement")

        module = imp.load_source(self._import_name(name), path)

        if not hasattr(module, "Module"):
            raise ModuleLoadException("module '%s' doesn't have a "
                "'Module' class." % name)
        if not inspect.isclass(module.Module):
            raise ModuleLoadException("module '%s' has a 'Module' attribute "
                "but it is not a class." % name)

        context = str(uuid.uuid4())
        context_events = self.events.new_context(context)
        context_exports = self.exports.new_context(context)
        context_timers = self.timers.new_context(context)
        module_object = module.Module(bot, context_events, context_exports,
            context_timers, self.log)

        if not hasattr(module_object, "_name"):
            module_object._name = name.title()
        for attribute_name in dir(module_object):
            attribute = getattr(module_object, attribute_name)
            for hook in self._get_magic(attribute,
                    utils.consts.BITBOT_HOOKS_MAGIC, []):
                context_events.on(hook["event"]).hook(attribute,
                    **hook["kwargs"])
        for export in self._get_magic(module_object,
                utils.consts.BITBOT_EXPORTS_MAGIC, []):
            context_exports.add(export["setting"], export["value"])

        module_object._context = context
        module_object._import_name = name

        if name in self.modules:
            raise ModuleNameCollisionException("Module name '%s' "
                "attempted to be used twice")
        return module_object

    def load_module(self, bot: "IRCBot.Bot", name: str):
        try:
            module = self._load_module(bot, name)
        except ModuleWarning as warning:
            self.log.error("Module '%s' not loaded", [name])
            raise
        except Exception as e:
            self.log.error("Failed to load module \"%s\": %s",
                [name, str(e)])
            raise

        self.modules[module._import_name] = module
        if name in self.waiting_requirement:
            for requirement_name in self.waiting_requirement:
                self.load_module(bot, requirement_name)
        self.log.debug("Module '%s' loaded", [name])

    def load_modules(self, bot: "IRCBot.Bot", whitelist: typing.List[str]=[],
            blacklist: typing.List[str]=[]):
        for path in self.list_modules():
            name = self._module_name(path)
            if name in whitelist or (not whitelist and not name in blacklist):
                try:
                    self.load_module(bot, name)
                except ModuleWarning:
                    pass

    def unload_module(self, name: str):
        if not name in self.modules:
            raise ModuleNotFoundException()
        module = self.modules[name]
        if hasattr(module, "unload"):
            try:
                module.unload()
            except:
                pass
        del self.modules[name]

        context = module._context
        self.events.purge_context(context)
        self.exports.purge_context(context)
        self.timers.purge_context(context)

        del sys.modules[self._import_name(name)]
        references = sys.getrefcount(module)
        referrers = gc.get_referrers(module)
        del module
        references -= 1 # 'del module' removes one reference
        references -= 1 # one of the refs is from getrefcount

        self.log.debug("Module '%s' unloaded (%d reference%s)",
            [name, references, "" if references == 1 else "s"])
        if references > 0:
            self.log.debug("References left for '%s': %s",
                [name, ", ".join([str(referrer) for referrer in referrers])])
