import itertools, time, traceback

PRIORITY_URGENT = 0
PRIORITY_HIGH = 1
PRIORITY_MEDIUM = 2
PRIORITY_LOW = 3
PRIORITY_MONITOR = 4

DEFAULT_PRIORITY = PRIORITY_MEDIUM
DEFAULT_EVENT_DELIMITER = "."
DEFAULT_MULTI_DELIMITER = "|"

class Event(object):
    def __init__(self, name, **kwargs):
        self.name = name
        self.kwargs = kwargs
        self.eaten = False
    def __getitem__(self, key):
        return self.kwargs[key]
    def get(self, key, default=None):
        return self.kwargs.get(key, default)
    def __contains__(self, key):
        return key in self.kwargs
    def eat(self):
        self.eaten = True

class EventCallback(object):
    def __init__(self, function, priority, kwargs):
        self.function = function
        self.priority = priority
        self.kwargs = kwargs
    def call(self, event):
        return self.function(event)

class MultipleEventHook(object):
    def __init__(self):
        self._event_hooks = set([])
    def _add(self, event_hook):
        self._event_hooks.add(event_hook)

    def hook(self, function, **kwargs):
        for event_hook in self._event_hooks:
            event_hook.hook(function, **kwargs)

    def call_limited(self, maximum, **kwargs):
        returns = []
        for event_hook in self._event_hooks:
            returns.append(event_hook.call_limited(maximum, **kwargs))
        return returns
    def call(self, **kwargs):
        returns = []
        for event_hook in self._event_hooks:
            returns.append(event_hook.call(**kwargs))
        return returns

class EventHookContext(object):
    def __init__(self, parent, context):
        self._parent = parent
        self.context = context
    def hook(self, function, priority=DEFAULT_PRIORITY, replay=False,
            **kwargs):
        self._parent._context_hook(self.context, function, priority, replay,
            kwargs)
    def on(self, subevent, *extra_subevents,
            delimiter=DEFAULT_EVENT_DELIMITER):
        return self._parent._context_on(self.context, subevent,
            extra_subevents, delimiter)
    def call_for_result(self, default=None, **kwargs):
        return self._parent.call_for_result(default, **kwargs)
    def assure_call(self, **kwargs):
        self._parent.assure_call(**kwargs)
    def call(self, **kwargs):
        return self._parent.call(**kwargs)
    def call_limited(self, maximum, **kwargs):
        return self._parent.call_limited(maximum, **kwargs)
    def get_hooks(self):
        return self._parent.get_hooks()
    def get_children(self):
        return self._parent.get_children()

class EventHook(object):
    def __init__(self, log, name=None, parent=None):
        self.log = log
        self.name = name
        self.parent = parent
        self._children = {}
        self._hooks = []
        self._stored_events = []
        self._context_hooks = {}

    def _make_event(self, kwargs):
        return Event(self.name, **kwargs)

    def _get_path(self):
        path = []
        parent = self
        while not parent == None and not parent.name == None:
            path.append(parent.name)
            parent = parent.parent
        return DEFAULT_EVENT_DELIMITER.join(path[::-1])

    def new_context(self, context):
        return EventHookContext(self, context)

    def hook(self, function, priority=DEFAULT_PRIORITY, replay=False,
            **kwargs):
        self._hook(function, None, priority, replay, kwargs)
    def _context_hook(self, context, function, priority, replay, kwargs):
        self._hook(function, context, priority, replay, kwargs)
    def _hook(self, function, context, priority, replay, kwargs):
        callback = EventCallback(function, priority, kwargs)

        if context == None:
            self._hooks.append(callback)
        else:
            if not context in self._context_hooks:
                self._context_hooks[context] = []
            self._context_hooks[context].append(callback)

        if replay and not self._stored_events == None:
            for kwargs in self._stored_events:
                self._call(kwargs)
        self._stored_events = None

    def _make_multiple_hook(self, source, context, events):
        multiple_event_hook = MultipleEventHook()
        for event in events:
            event_hook = source.get_child(event)
            if not context == None:
                event_hook = event_hook.new_context(context)
            multiple_event_hook._add(event_hook)
        return multiple_event_hook

    def on(self, subevent, *extra_subevents,
            delimiter=DEFAULT_EVENT_DELIMITER):
        return self._on(subevent, extra_subevents, None, delimiter)
    def _context_on(self, context, subevent, extra_subevents,
            delimiter=DEFAULT_EVENT_DELIMITER):
        return self._on(subevent, extra_subevents, context, delimiter)
    def _on(self, subevent, extra_subevents, context, delimiter):
        if delimiter in subevent:
            event_chain = subevent.split(delimiter)
            event_obj = self
            for event_name in event_chain:
                if DEFAULT_MULTI_DELIMITER in event_name:
                    return self._make_multiple_hook(event_obj, context,
                        event_name.split(DEFAULT_MULTI_DELIMITER))

                event_obj = event_obj.get_child(event_name)
            if not context == None:
                return event_obj.new_context(context)
            return event_obj

        if extra_subevents:
            return self._make_multiple_hook(self, context,
                (subevent,)+extra_subevents)

        child = self.get_child(subevent)
        if not context == None:
            child = child.new_context(context)
        return child

    def call_for_result(self, default=None, **kwargs):
        results = self.call_limited(1, **kwargs)
        return default if not len(results) else results[0]
    def assure_call(self, **kwargs):
        if not self._stored_events == None:
            self._stored_events.append(kwargs)
        else:
            self._call(kwargs)
    def call(self, **kwargs):
        return self._call(kwargs)
    def call_limited(self, maximum, **kwargs):
        return self._call(kwargs, maximum=maximum)
    def _call(self, kwargs, maximum=None):
        event_path = self._get_path()
        self.log.debug("calling event: \"%s\" (params: %s)",
            [event_path, kwargs])
        start = time.monotonic()

        event = self._make_event(kwargs)
        returns = []
        for hook in self.get_hooks()[:maximum]:
            if event.eaten:
                break
            try:
                returns.append(hook.call(event))
            except Exception as e:
                traceback.print_exc()
                self.log.error("failed to call event \"%s\"", [
                    event_path], exc_info=True)

        total_milliseconds = (time.monotonic() - start) * 1000
        self.log.debug("event \"%s\" called in %fms", [
            event_path, total_milliseconds])

        self.check_purge()

        return returns

    def get_child(self, child_name):
        child_name_lower = child_name.lower()
        if not child_name_lower in self._children:
            self._children[child_name_lower] = EventHook(self.log,
                child_name_lower)
        return self._children[child_name_lower]
    def remove_child(self, child_name):
        child_name_lower = child_name.lower()
        if child_name_lower in self._children:
            del self._children[child_name_lower]

    def check_purge(self):
        if self.is_empty() and not self.parent == None:
            self.parent.remove_child(self.name)
            self.parent.check_purge()

    def remove_context(self, context):
        del self._context_hooks[context]
    def has_context(self, context):
        return context in self._context_hooks
    def purge_context(self, context):
        if self.has_context(context):
            self.remove_context(context)

        for child_name in self.get_children()[:]:
            child = self.get_child(child_name)
            child.purge_context(context)

    def get_hooks(self):
        return sorted(self._hooks + sum(self._context_hooks.values(), []),
            key=lambda e: e.priority)
    def get_children(self):
        return list(self._children.keys())
    def is_empty(self):
        return len(self.get_hooks() + self.get_children()) == 0
