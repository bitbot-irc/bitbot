import itertools, time, traceback

PRIORITY_URGENT = 0
PRIORITY_HIGH = 1
PRIORITY_MEDIUM = 2
PRIORITY_LOW = 3

DEFAULT_PRIORITY = PRIORITY_LOW
DEFAULT_DELIMITER = "."

class Event(object):
    def __init__(self, bot, name, **kwargs):
        self.bot = bot
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
    def __init__(self, function, bot, priority, kwargs):
        self.function = function
        self.bot = bot
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
    def hook(self, function, priority=DEFAULT_PRIORITY, **kwargs):
        self._parent._context_hook(self.context, function, priority, kwargs)
    def on(self, subevent, *extra_subevents, delimiter=DEFAULT_DELIMITER):
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
    def __init__(self, bot, name=None, parent=None):
        self.bot = bot
        self.name = name
        self.parent = parent
        self._children = {}
        self._hooks = []
        self._stored_events = []
        self._context_hooks = {}
        self._current_context = None

    def _make_event(self, kwargs):
        return Event(self.bot, self.name, **kwargs)

    def _get_path(self):
        path = [self.name]
        parent = self.parent
        while not parent == None and not parent.name == None:
            path.append(parent.name)
            parent = parent.parent
        return DEFAULT_DELIMITER.join(path[::-1])

    def new_context(self, context):
        return EventHookContext(self, context)

    def hook(self, function, priority=DEFAULT_PRIORITY, replay=False,
            **kwargs):
        self._hook(function, None, priority, replay, kwargs)
    def _context_hook(self, context, function, priority, kwargs):
        self._hook(function, context, priority, False, kwargs)
    def _hook(self, function, context, priority, replay, kwargs):
        callback = EventCallback(function, self.bot, priority, kwargs)

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

    def on(self, subevent, *extra_subevents, delimiter=DEFAULT_DELIMITER):
        return self._on(subevent, extra_subevents, None, delimiter)
    def _context_on(self, context, subevent, extra_subevents,
            delimiter=DEFAULT_DELIMITER):
        return self._on(subevent, extra_subevents, context, delimiter)
    def _on(self, subevent, extra_subevents, context, delimiter):
        if delimiter in subevent:
            event_chain = subevent.split(delimiter)
            event_obj = self
            for event_name in event_chain:
                event_obj = event_obj.get_child(event_name)
            if not context == None:
                event_obj = event_obj.new_context(context)
            return event_obj

        if extra_subevents:
            multiple_event_hook = MultipleEventHook()
            for extra_subevent in (subevent,)+extra_subevents:
                child = self.get_child(extra_subevent)
                if not context == None:
                    child = child.new_context(context)
                multiple_event_hook._add(child)
            return multiple_event_hook

        child = self.get_child(subevent)
        if not context == None:
            child = child.new_context(context)
        return child

    def call_for_result(self, default=None, **kwargs):
        results = self.call_limited(0, **kwargs)
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
        self.bot.log.debug("calling event: \"%s\" (params: %s)",
            [event_path, kwargs])
        start = time.monotonic()

        event = self._make_event(kwargs)
        called = 0
        returns = []
        for hook in self.get_hooks():
            if (maximum and called == maximum) or event.eaten:
                break
            try:
                returns.append(hook.call(event))
            except Exception as e:
                traceback.print_exc()
                self.bot.log.error("failed to call event \"%s", [
                    event_path], exc_info=True)
            called += 1

        end = time.monotonic()
        total_milliseconds = (end - start) * 1000
        self.bot.log.debug("event \"%s\" called in %fms", [
            event_path, total_milliseconds])

        self.check_purge()

        return returns

    def get_child(self, child_name):
        child_name_lower = child_name.lower()
        if not child_name_lower in self._children:
            self._children[child_name_lower] = EventHook(self.bot,
                child_name_lower, self)
        return self._children[child_name_lower]
    def remove_child(self, child_name):
        child_name_lower = child_name.lower()
        if child_name_lower in self._children:
            del self._children[child_name_lower]
    def get_children(self):
        return self._children.keys()

    def check_purge(self):
        if len(self.get_hooks()) == 0 and len(self._children
                ) == 0 and not self.parent == None:
            self.parent.remove_child(self.name)
            self.parent.check_purge()

    def remove_context(self, context):
        del self._context_hooks[context]
    def has_context(self, context):
        return context in self._context_hooks
    def purge_context(self, context):
        if self.has_context(context):
            self.remove_context(context)
        for child in self.get_children():
            child.purge_context(context)

    def get_hooks(self):
        return sorted(self._hooks + list(itertools.chain.from_iterable(
            self._context_hooks.values())), key=lambda e: e.priority)
