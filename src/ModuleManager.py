import enum, gc, glob, importlib, importlib.util, io, inspect, os, sys
import typing, uuid
from src import Config, EventManager, Exports, IRCBot, Logging, Timers, utils

class ModuleException(Exception):
    pass
class ModuleWarning(Exception):
    pass

class ModuleNotLoadedException(ModuleException):
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
class ModuleNotLoadableWarning(ModuleWarning):
    pass

class ModuleDependencyNotFulfilled(ModuleException):
    def __init__(self, module, dependency):
        ModuleException.__init__(self, "Dependency for %s not fulfilled: %s"
            % (module, dependency))
        self.module = module
        self.dependency = dependency
class ModuleCircularDependency(ModuleException):
    pass

class ModuleType(enum.Enum):
    FILE = 0
    DIRECTORY = 1

class TryReloadResult(object):
    def __init__(self, success: bool, message: str):
        self.success = success
        self.message = message

class BaseModule(object):
    def __init__(self,
            bot: "IRCBot.Bot",
            events: EventManager.Events,
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
    def unload(self):
        pass

    def on_pause(self):
        pass
    def on_resume(self):
        pass

class ModuleDefinition(object):
    def __init__(self,
            name: str,
            filename: str,
            type: ModuleType,
            hashflags: typing.List[typing.Tuple[str, typing.Optional[str]]]):
        self.name = name
        self.filename = filename
        self.type = type
        self.hashflags = hashflags
    def get_dependencies(self):
        dependencies = []
        for key, value in self.hashflags:
            if key == "depends-on":
                dependencies.append(value)
        return sorted(dependencies)

class LoadedModule(object):
    def __init__(self,
            name: str,
            title: str,
            module: BaseModule,
            context: str,
            import_name: str):
        self.name = name
        self.title = title
        self.module = module
        self.context = context
        self.import_name = import_name

class ModuleManager(object):
    def __init__(self,
            events: EventManager.Events,
            exports: Exports.Exports,
            timers: Timers.Timers,
            config: Config.Config,
            log: Logging.Log,
            core_modules: str,
            extra_modules: typing.List[str]):
        self.events = events
        self.exports = exports
        self.config = config
        self.timers = timers
        self.log = log
        self._core_modules = core_modules
        self._extra_modules = extra_modules

        self.modules = {} # type: typing.Dict[str, LoadedModule]

    def _list_modules(self, directory: str
            ) -> typing.Dict[str, ModuleDefinition]:
        modules = []
        for file_module in glob.glob(os.path.join(directory, "*.py")):
            modules.append(self.define_module(ModuleType.FILE, file_module))

        for directory_module in glob.glob(os.path.join(
                directory, "*", "__init__.py")):
            modules.append(self.define_module(ModuleType.DIRECTORY,
                directory_module))
        return {definition.name: definition for definition in modules}

    def list_modules(self, whitelist: typing.List[str],
            blacklist: typing.List[str]) -> typing.Dict[str, ModuleDefinition]:
        core_modules = self._list_modules(self._core_modules)
        extra_modules = {}

        for directory in self._extra_modules:
            for name, module in self._list_modules(directory).items():
                if (not name in extra_modules and
                        (name in whitelist or
                        (not whitelist and not name in blacklist))):
                    extra_modules[name] = module

        modules = {}
        modules.update(extra_modules)
        modules.update(core_modules)
        return modules

    def define_module(self, type: ModuleType, filename: str
            ) -> ModuleDefinition:
        if type == ModuleType.DIRECTORY:
            name = os.path.dirname(filename)
        else:
            name = filename
        name = self._module_name(name)

        return ModuleDefinition(name, filename, type,
            utils.parse.hashflags(filename))

    def find_module(self, name: str) -> ModuleDefinition:
        type = ModuleType.FILE
        paths = self._module_paths(name)

        path = None
        for path in paths:
            if os.path.isdir(path):
                type = ModuleType.DIRECTORY
                path = os.path.join(path, "__init__.py")
            else:
                possible_path = "%s.py" % path
                if os.path.isfile(possible_path):
                    path = possible_path

            if path:
                break

        if not path:
            raise ModuleNotFoundException(name)

        return self.define_module(type, path)

    def _module_name(self, path: str) -> str:
        return os.path.basename(path).rsplit(".py", 1)[0].lower()
    def _module_paths(self, name: str) -> typing.List[str]:
        paths = []
        for directory in self.directories:
            paths.append(os.path.join(directory, name))
        return paths
    def _import_name(self, name: str, context: str) -> str:
        return "%s_%s" % (name, context)

    def from_context(self, context: str) -> typing.Optional[LoadedModule]:
        for module in self.modules.values():
            if module.context == context:
                return module
        return None
    def from_name(self, name: str) -> typing.Optional[LoadedModule]:
        name_lower = name.lower()
        for module in self.modules.values():
            if module.name.lower() == name_lower:
                return module
        return None

    def _check_hashflags(self, bot: "IRCBot.Bot", definition: ModuleDefinition
            ) -> None:
        for hashflag, value in definition.hashflags:
            if hashflag == "ignore":
               # nope, ignore this module.
               raise ModuleNotLoadableWarning("module ignored")

            elif hashflag == "require-config" and value:
                if not self.config.get(value.lower(), None):
                    # nope, required config option not present.
                    raise ModuleNotLoadableWarning(
                        "required config not present")

    def _load_module(self, bot: "IRCBot.Bot", definition: ModuleDefinition,
            check_dependency: bool=True) -> LoadedModule:
        if check_dependency:
            dependencies = definition.get_dependencies()
            for dependency in dependencies:
                if not dependency in self.modules:
                    raise ModuleDependencyNotFulfilled(definition.name,
                        dependency)

        self._check_hashflags(bot, definition)

        context = str(uuid.uuid4())
        import_name = self._import_name(definition.name, context)

        import_spec = importlib.util.spec_from_file_location(import_name,
            definition.filename)
        module = importlib.util.module_from_spec(import_spec)
        sys.modules[import_name] = module
        loader = typing.cast(importlib.abc.Loader, import_spec.loader)
        loader.exec_module(module)

        module_object_pointer = getattr(module, "Module", None)
        if not module_object_pointer:
            raise ModuleLoadException("module '%s' doesn't have a "
                "'Module' class." % definition.name)
        if not inspect.isclass(module_object_pointer):
            raise ModuleLoadException("module '%s' has a 'Module' attribute "
                "but it is not a class." % definition.name)

        context_events = self.events.new_context(context)
        context_exports = self.exports.new_context(context)
        context_timers = self.timers.new_context(context)
        module_object = module_object_pointer(bot, context_events,
            context_exports, context_timers, self.log)

        module_title = (getattr(module_object, "_name", None) or
            definition.name.title())

        # @utils.hook() magic
        for attribute_name in dir(module_object):
            attribute = getattr(module_object, attribute_name)
            if (inspect.ismethod(attribute) and
                    utils.decorators.has_magic(attribute)):
                magic = utils.decorators.get_magic(attribute)

                for hook, kwargs in magic.get_hooks():
                    context_events.on(hook)._hook(attribute, kwargs=kwargs)

        # @utils.export() magic
        if utils.decorators.has_magic(module_object):
            magic = utils.decorators.get_magic(module_object)
            for key, value in magic.get_exports():
                context_exports.add(key, value)

        if definition.name in self.modules:
            raise ModuleNameCollisionException("Module name '%s' "
                "attempted to be used twice" % definition.name)

        return LoadedModule(definition.name, module_title, module_object,
            context, import_name)

    def load_module(self, bot: "IRCBot.Bot", definition: ModuleDefinition
            ) -> LoadedModule:
        try:
            loaded_module = self._load_module(bot, definition,
                check_dependency=False)
        except ModuleWarning as warning:
            self.log.warn("Module '%s' not loaded", [definition.name])
            raise
        except Exception as e:
            self.log.error("Failed to load module \"%s\": %s",
                [definition.name, str(e)])
            raise

        self.modules[loaded_module.name] = loaded_module
        self.log.debug("Module '%s' loaded", [loaded_module.name])
        return loaded_module

    def _dependency_sort(self, definitions: typing.Dict[str, ModuleDefinition]
            ) -> typing.List[ModuleDefinition]:
        definitions_ordered = []

        definition_names = {d.name: d for d in definitions}
        definition_dependencies = {
            d.name: d.get_dependencies() for d in definitions}

        for name, deps in list(definition_dependencies.items())[:]:
            for dep in deps:
                if not dep in definition_dependencies:
                    # unknown dependency!
                    self.log.warn(
                        "Module '%s' not loaded - unfulfilled dependency '%s'" %
                        (name, dep))
                    del definition_dependencies[name]

        while definition_dependencies:
            changed = False

            to_remove = []
            for name, dependencies in definition_dependencies.items():
                if not dependencies:
                    changed = True
                    # pop things with no unfufilled dependencies
                    to_remove.append(name)
            for name in to_remove:
                definitions_ordered.append(name)
                del definition_dependencies[name]
                for deps in definition_dependencies.values():
                    if name in deps:
                        changed = True
                        # fulfill dependencies for things we just popped
                        deps.remove(name)

            if not changed:
                for name, deps in definition_dependencies.items():
                    for dep_name in deps:
                        if name in definition_dependencies[dep_name]:
                            self.log.warn(
                                "Direct circular dependency detected: %s<->%s",
                                [name, dep_name])
                            changed = True
                            # snap a circular dependence
                            deps.remove(dep_name)
                            definition_dependencies[dep_name].remove(name)
            if not changed:
                raise ModuleCircularDependency()

        return [definition_names[name] for name in definitions_ordered]

    def load_modules(self, bot: "IRCBot.Bot", whitelist: typing.List[str]=[],
            blacklist: typing.List[str]=[]
            ) -> None:
        loadable, nonloadable = self._list_valid_modules(bot, whitelist, blacklist)

        for definition in nonloadable:
            self.log.warn("Not loading module '%s'", [definition.name])

        for definition in loadable:
            self.load_module(bot, definition)

    def unload_module(self, name: str):
        if not name in self.modules:
            raise ModuleNotLoadedException(name)
        loaded_module = self.modules[name]
        self._unload_module(loaded_module)
        del self.modules[loaded_module.name]

    def _unload_module(self, loaded_module: LoadedModule):
        if hasattr(loaded_module.module, "unload"):
            try:
                loaded_module.module.unload()
            except:
                pass

        context = loaded_module.context
        self.events.purge_context(context)
        self.exports.purge_context(context)
        self.timers.purge_context(context)

        module = loaded_module.module
        del loaded_module.module

        del sys.modules[loaded_module.import_name]
        namespace = "%s." % loaded_module.import_name
        for import_name in list(sys.modules.keys()):
            if import_name.startswith(namespace):
                del sys.modules[import_name]

        references = sys.getrefcount(module)
        referrers = gc.get_referrers(module)
        del module
        references -= 1 # 'del module' removes one reference
        references -= 1 # one of the refs is from getrefcount

        self.log.debug("Module '%s' unloaded (%d reference%s)",
            [loaded_module.name, references,
            "" if references == 1 else "s"])
        if references > 0:
            self.log.debug("References left for '%s': %s",
                [loaded_module.name,
                ", ".join([str(referrer) for referrer in referrers])])

    def try_reload_modules(self, bot: "IRCBot.Bot",
            whitelist: typing.List[str], blacklist: typing.List[str]):
        loadable, nonloadable = self._list_valid_modules(
            bot, whitelist, blacklist)

        old_modules = self.modules
        self.modules = {}

        for module in old_modules.values():
            module.module.on_pause()

        failed = None
        for definition in loadable:
            try:
                self.load_module(bot, definition)
            except Exception as e:
                failed = (definition, e)
                break

        if failed is not None:
            for module in self.modules.values():
                self._unload_module(module)
            self.modules = old_modules
            for module in old_modules.values():
                module.module.on_resume()

            definition, exception = failed
            return TryReloadResult(False,
                "Failed to load %s (%s), rolling back reload" %
                (definition.name, str(exception)))
        else:
            for module in old_modules.values():
                self._unload_module(module)
            return TryReloadResult(True, "Reloaded %d modules" %
                len(self.modules.keys()))

    def _list_valid_modules(self, bot: "IRCBot.Bot",
            whitelist: typing.List[str], blacklist: typing.List[str]):
        module_definitions = self.list_modules(whitelist, blacklist)

        loadable_definitions = []
        nonloadable_definitions = []
        for name, definition in module_definitions.items():
            try:
                self._check_hashflags(bot, definition)
            except ModuleNotLoadableWarning:
                nonloadable_definitions.append(definition)
                continue
            loadable_definitions.append(definition)

        return (self._dependency_sort(loadable_definitions),
            nonloadable_definitions)
