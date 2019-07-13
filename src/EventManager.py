import itertools, time, traceback, typing
from src import Logging, utils

PRIORITY_URGENT = 0
PRIORITY_HIGH = 1
PRIORITY_MEDIUM = 2
PRIORITY_LOW = 3
PRIORITY_MONITOR = 4

DEFAULT_PRIORITY = PRIORITY_MEDIUM
DEFAULT_EVENT_DELIMITER = "."
DEFAULT_MULTI_DELIMITER = "|"

CALLBACK_TYPE = typing.Callable[["Event"], typing.Any]

class Event(object):
    def __init__(self, name: str, kwargs):
        self.name = name
        self.kwargs = kwargs
        self.eaten = False
    def __getitem__(self, key: str) -> typing.Any:
        return self.kwargs[key]
    def get(self, key: str, default=None) -> typing.Any:
        return self.kwargs.get(key, default)
    def __contains__(self, key: str) -> bool:
        return key in self.kwargs
    def eat(self):
        self.eaten = True

class EventHook(object):
    def __init__(self, event_name: str, func: CALLBACK_TYPE,
            context: typing.Optional[str], priority: int, kwargs: dict):
        self.event_name = event_name
        self.function = func
        self.context = context
        self.priority = priority
        self._kwargs = kwargs
        self.docstring = utils.parse.docstring(func.__doc__ or "")

    def call(self, event: Event) -> typing.Any:
        return self.function(event)

    def get_kwarg(self, name: str, default=None) -> typing.Any:
        if name in self._kwargs:
            return self._kwargs[name]
        elif name in self.docstring.items:
            return self.docstring.items[name]
        return default

class Events(object):
    def __init__(self, root: "EventRoot", path: typing.List[str],
            context: typing.Optional[str]):
        self._root = root
        self._path = path
        self._context = context

    def new_root(self):
        return self._root._new_root()

    def new_context(self, context: str):
        return self._root._new_context(context)

    def make_event(self, **kwargs):
        return self._root._make_event(self._path, kwargs)

    def on(self, subname):
        parts = subname.split(DEFAULT_EVENT_DELIMITER)
        new_path = self._path + parts

        return Events(self._root, new_path, self._context)

    def hook(self, func: CALLBACK_TYPE, priority: int = DEFAULT_PRIORITY,
            **kwargs):
        self._root._hook(self._path, func, self._context, priority, kwargs)

    def call(self, **kwargs):
        return self._root._call(self._path, kwargs, True, self._context, None)
    def call_unsafe(self, **kwargs):
        return self._root._call(self._path, kwargs, False, self._context, None)

    def _call_limited(self, maximum: int, safe: bool, kwargs):
        return self._root._call(self._path, kwargs, safe, self._context,
            maximum)
    def call_limited(self, maximum: int, **kwargs):
        return self._call_limited(maximum, True, kwargs)
    def call_limited_unsafe(self, maximum: int, **kwargs):
        return self._call_limited(maximum, False, kwargs)

    def call_for_result(self, default=None, **kwargs):
        return (self._call_limited(1, True, kwargs) or [default])[0]
    def call_for_result_unsafe(self, default=None, **kwargs):
        return (self._call_limited(1, False, kwargs) or [default])[0]

    def get_children(self):
        return self._root._get_children(self._path)
    def get_hooks(self):
        return self._root._get_hooks(self._path)

    def purge_context(self, context: str):
        self._root._purge_context(context)

class EventRoot(object):
    def __init__(self, log: Logging.Log):
        self.log = log
        self._hooks: typing.Dict[str, typing.List[EventHook]] = {}

    def _make_event(self, path: typing.List[str], kwargs: dict):
        return Event(self._path_str(path), kwargs)

    def _new_context(self, context: str):
        return Events(self, [], context)
    def _new_root(self):
        return EventRoot(self.log).wrap()

    def wrap(self):
        return Events(self, [], None)

    def _path_str(self, path: typing.List[str]):
        path_lower = [p.lower() for p in path]
        return DEFAULT_EVENT_DELIMITER.join(path_lower)

    def _hook(self, path: typing.List[str], func: CALLBACK_TYPE,
            context: typing.Optional[str], priority: int, kwargs: dict
            ) -> EventHook:
        path_str = self._path_str(path)
        new_hook = EventHook(path_str, func, context, priority, kwargs)

        if not path_str in self._hooks:
            self._hooks[path_str] = []
        hook_array = self._hooks[path_str]

        hooked = False
        for i, other_hook in enumerate(hook_array):
            if other_hook.priority > new_hook.priority:
                hooked = True
                hook_array.insert(i, new_hook)
                break
        if not hooked:
            hook_array.append(new_hook)
        return new_hook

    def _call(self, path: typing.List[str], kwargs: dict, safe: bool,
            context: typing.Optional[str], maximum: typing.Optional[int]
            ) -> typing.List[typing.Any]:
        if not utils.is_main_thread():
            raise RuntimeError("Can't call events outside of main thread")

        returns: typing.List[typing.Any] = []
        path_str = self._path_str(path)
        if not path_str in self._hooks:
            self.log.trace("not calling non-hooked event \"%s\" (params: %s)",
                [path_str, kwargs])
            return returns

        self.log.trace("calling event: \"%s\" (params: %s)",
            [path_str, kwargs])
        start = time.monotonic()

        hooks = self._hooks[path_str]
        if maximum:
            hooks = hooks[:maximum]
        event = self._make_event(path, kwargs)

        for hook in hooks:
            if event.eaten:
                break

            try:
                returned = hook.call(event)
            except Exception as e:
                if safe:
                    self.log.error("failed to call event \"%s\"",
                        [path_str], exc_info=True)
                    continue
                else:
                    raise
            returns.append(returned)

        total_milliseconds = (time.monotonic() - start) * 1000
        self.log.trace("event \"%s\" called in %fms",
            [path_str, total_milliseconds])

        return returns

    def _purge_context(self, context: str):
        context_hooks: typing.Dict[str, typing.List[EventHook]] = {}
        for path in self._hooks.keys():
            for hook in self._hooks[path]:
                if hook.context == context:
                    if not path in context_hooks:
                        context_hooks[path] = []
                    context_hooks[path].append(hook)
        for path in context_hooks:
            for hook in context_hooks[path]:
                self._hooks[path].remove(hook)
                if not self._hooks[path]:
                    del self._hooks[path]

    def _get_children(self, path):
        path_prefix = "%s%s" % (self._path_str(path), DEFAULT_EVENT_DELIMITER)
        matches = []
        for key in self._hooks.keys():
            if key.startswith(path_prefix):
                matches.append(key.replace(path_prefix, "", 1))
        return matches
    def _get_hooks(self, path):
        path_str = self._path_str(path)
        if path_str in self._hooks:
            return self._hooks[path_str][:]
        return []
