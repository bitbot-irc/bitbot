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
    def __init__(self, name: str, **kwargs):
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

class EventCallback(object):
    def __init__(self, function: CALLBACK_TYPE, priority: int, kwargs: dict):
        self.function = function
        self.priority = priority
        self.kwargs = kwargs
        self.docstring = utils.parse.docstring(function.__doc__ or "")

    def call(self, event: Event) -> typing.Any:
        return self.function(event)

    def get_kwarg(self, name: str, default=None) -> typing.Any:
        item = self.kwargs.get(name, default)
        return item or self.docstring.items.get(name, default)

class EventHook(object):
    def __init__(self, log: Logging.Log, name: str = None,
            parent: "EventHook" = None):
        self.log = log
        self.name = name
        self.parent = parent
        self._children = {}
        self._hooks = []
        self._replayed = False
        self._stored_events = []
        self._context_hooks = {}

    def _make_event(self, kwargs: dict) -> Event:
        return Event(self._get_path(), **kwargs)

    def _get_path(self) -> str:
        path = []
        parent = self # type: typing.Optional[EventHook]
        while not parent == None:
            cast_parent = typing.cast(EventHook, parent)
            if cast_parent.name == None:
                break

            path.append(typing.cast(str, cast_parent.name))
            parent = cast_parent.parent
        return DEFAULT_EVENT_DELIMITER.join(path[::-1])

    def new_context(self, context: str) -> "EventHookContext":
        return EventHookContext(self, context)

    def hook(self, function: CALLBACK_TYPE, priority: int = DEFAULT_PRIORITY,
            replay: bool = False, **kwargs) -> EventCallback:
        return self._hook(function, None, priority, replay, kwargs)
    def _context_hook(self, context: str, function: CALLBACK_TYPE,
            priority: int, replay: bool, kwargs: dict) -> EventCallback:
        return self._hook(function, context, priority, replay, kwargs)
    def _hook(self, function: CALLBACK_TYPE, context: typing.Optional[str],
            priority: int, replay: bool, kwargs: dict) -> EventCallback:
        callback = EventCallback(function, priority, kwargs)

        if context == None:
            self._hooks.append(callback)
        else:
            if not context in self._context_hooks:
                self._context_hooks[context] = []
            self._context_hooks[context].append(callback)

        if replay and not self._replayed:
            for kwargs in self._stored_events:
                self._call(kwargs, True, None)
        self._replayed = True
        return callback

    def unhook(self, callback: "EventHook"):
        if callback in self._hooks:
            self._hooks.remove(callback)

        empty = []
        for context, hooks in self._context_hooks.items():
            if callback in hooks:
                hooks.remove(callback)
                if not hooks:
                    empty.append(context)
        for context in empty:
            del self._context_hooks[context]

    def _make_multiple_hook(self, source: "EventHook",
            context: typing.Optional[str],
            events: typing.Iterable[str]) -> "MultipleEventHook":
        multiple_event_hook = MultipleEventHook()
        for event in events:
            event_hook = source.get_child(event)
            if not context == None:
                context_hook = event_hook.new_context(typing.cast(str, context))
                multiple_event_hook._add(typing.cast(EventHook, context_hook))
            else:
                multiple_event_hook._add(event_hook)
        return multiple_event_hook

    def on(self, subevent: str, *extra_subevents: str,
            delimiter: str = DEFAULT_EVENT_DELIMITER) -> "EventHook":
        return self._on(subevent, extra_subevents, None, delimiter)
    def _context_on(self, context: str, subevent: str,
            extra_subevents: typing.Tuple[str, ...],
            delimiter: str = DEFAULT_EVENT_DELIMITER) -> "EventHook":
        return self._on(subevent, extra_subevents, context, delimiter)
    def _on(self, subevent: str, extra_subevents: typing.Tuple[str, ...],
            context: typing.Optional[str], delimiter: str) -> "EventHook":
        if delimiter in subevent:
            event_chain = subevent.split(delimiter)
            event_obj = self
            for event_name in event_chain:
                if DEFAULT_MULTI_DELIMITER in event_name:
                    multiple_hook = self._make_multiple_hook(event_obj, context,
                        event_name.split(DEFAULT_MULTI_DELIMITER))
                    return typing.cast(EventHook, multiple_hook)

                event_obj = event_obj.get_child(event_name)
            if not context == None:
                context_hook = event_obj.new_context(typing.cast(str, context))
                return typing.cast(EventHook, context_hook)
            return event_obj

        if extra_subevents:
            multiple_hook = self._make_multiple_hook(self, context,
                (subevent,)+extra_subevents)
            return typing.cast(EventHook, multiple_hook)

        child = self.get_child(subevent)
        if not context == None:
            context_child = child.new_context(typing.cast(str, context))
            child = typing.cast(EventHook, context_child)
        return child

    def call_for_result(self, default=None, **kwargs) -> typing.Any:
        return (self.call_limited(1, **kwargs) or [default])[0]
    def assure_call(self, **kwargs):
        if not self._replayed:
            self._stored_events.append(kwargs)
        else:
            self._call(kwargs, True, None)
    def call(self, **kwargs) -> typing.List[typing.Any]:
        return self._call(kwargs, True, None)
    def call_limited(self, maximum: int, **kwargs) -> typing.List[typing.Any]:
        return self._call(kwargs, True, maximum)

    def call_unsafe_for_result(self, default=None, **kwargs) -> typing.Any:
        return (self.call_unsafe_limited(1, **kwargs) or [default])[0]
    def call_unsafe(self, **kwargs) -> typing.List[typing.Any]:
        return self._call(kwargs, False, None)
    def call_unsafe_limited(self, maximum: int, **kwargs
            ) -> typing.List[typing.Any]:
        return self._call(kwargs, False, maximum)

    def _call(self, kwargs: dict, safe: bool, maximum: typing.Optional[int]
            ) -> typing.List[typing.Any]:
        event_path = self._get_path()
        start = time.monotonic()

        event = self._make_event(kwargs)
        returns = []
        for hook in self.get_hooks()[:maximum]:
            if event.eaten:
                break
            try:
                returns.append(hook.call(event))
            except Exception as e:
                if safe:
                    self.log.error("failed to call event \"%s\"",
                        [self._get_path()], exc_info=True)
                else:
                    raise

        total_milliseconds = (time.monotonic() - start) * 1000
        self.log.trace("called event in %fms: \"%s\" (params: %s)",
            [total_milliseconds, event_path, kwargs])

        self.check_purge()

        return returns

    def get_child(self, child_name: str) -> "EventHook":
        child_name_lower = child_name.lower()
        if not child_name_lower in self._children:
            self._children[child_name_lower] = EventHook(self.log,
                child_name_lower, self)
        return self._children[child_name_lower]
    def remove_child(self, child_name: str):
        child_name_lower = child_name.lower()
        if child_name_lower in self._children:
            del self._children[child_name_lower]

    def check_purge(self):
        if self.is_empty() and not self.parent == None:
            self.parent.remove_child(self.name)
            self.parent.check_purge()

    def remove_context(self, context: str):
        del self._context_hooks[context]
    def has_context(self, context: str) -> bool:
        return context in self._context_hooks
    def purge_context(self, context: str):
        if self.has_context(context):
            self.remove_context(context)

        for child_name in self.get_children()[:]:
            child = self.get_child(child_name)
            child.purge_context(context)

    def get_hooks(self) -> typing.List[EventCallback]:
        return sorted(self._hooks + sum(self._context_hooks.values(), []),
            key=lambda e: e.priority)
    def get_children(self) -> typing.List[str]:
        return list(self._children.keys())
    def is_empty(self) -> bool:
        return (len(self.get_hooks())+len(self.get_children())) == 0

class MultipleEventHook(object):
    def __init__(self):
        self._event_hooks = set([])
    def _add(self, event_hook: EventHook):
        self._event_hooks.add(event_hook)

    def hook(self, function: CALLBACK_TYPE, **kwargs):
        for event_hook in self._event_hooks:
            event_hook.hook(function, **kwargs)

    def call_limited(self, maximum: int, **kwargs) -> typing.List[typing.Any]:
        returns = []
        for event_hook in self._event_hooks:
            returns.append(event_hook.call_limited(maximum, **kwargs))
        return returns
    def call(self, **kwargs) -> typing.List[typing.Any]:
        returns = []
        for event_hook in self._event_hooks:
            returns.append(event_hook.call(**kwargs))
        return returns

class EventHookContext(object):
    def __init__(self, parent, context):
        self._parent = parent
        self.context = context
    def hook(self, function: CALLBACK_TYPE, priority: int = DEFAULT_PRIORITY,
            replay: bool = False, **kwargs) -> EventCallback:
        return self._parent._context_hook(self.context, function, priority,
            replay, kwargs)
    def unhook(self, callback: EventCallback):
        self._parent.unhook(callback)

    def on(self, subevent: str, *extra_subevents,
            delimiter: str = DEFAULT_EVENT_DELIMITER) -> EventHook:
        return self._parent._context_on(self.context, subevent,
            extra_subevents, delimiter)

    def call_for_result(self, default=None, **kwargs) -> typing.Any:
        return self._parent.call_for_result(default, **kwargs)
    def assure_call(self, **kwargs):
        self._parent.assure_call(**kwargs)
    def call(self, **kwargs) -> typing.List[typing.Any]:
        return self._parent.call(**kwargs)
    def call_limited(self, maximum: int, **kwargs) -> typing.List[typing.Any]:
        return self._parent.call_limited(maximum, **kwargs)

    def call_unsafe_for_result(self, default=None, **kwargs) -> typing.Any:
        return self._parent.call_unsafe_for_result(default, **kwargs)
    def call_unsafe(self, **kwargs) -> typing.List[typing.Any]:
        return self._parent.call_unsafe(**kwargs)
    def call_unsafe_limited(self, maximum: int, **kwargs
            ) -> typing.List[typing.Any]:
        return self._parent.call_unsafe_limited(maximum, **kwargs)

    def get_hooks(self) -> typing.List[EventCallback]:
        return self._parent.get_hooks()
    def get_children(self) -> typing.List[EventHook]:
        return self._parent.get_children()
