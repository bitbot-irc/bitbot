import time, traceback

PRIORITY_URGENT = 0
PRIORITY_HIGH = 1
PRIORITY_MEDIUM = 2
PRIORITY_LOW = 3

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
    def __init__(self, function, bot, priority, **kwargs):
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
    def call(self, max=None, **kwargs):
        for event_hook in self._event_hooks:
            event_hook.call(max, **kwargs)

class EventHook(object):
    def __init__(self, bot, name=None, parent=None):
        self.bot = bot
        self.name = name
        self.parent = parent
        self._children = {}
        self._hooks = []
        self._hook_notify = None
        self._child_notify = None
        self._call_notify = None
        self._stored_events = []

    def _make_event(self, kwargs):
        return Event(self.bot, self.name, **kwargs)

    def _get_path(self):
        path = [self.name]
        parent = self.parent
        while not parent == None and not parent.name == None:
            path.append(parent.name)
            parent = parent.parent
        return ".".join(path[::-1])

    def hook(self, function, priority=PRIORITY_LOW, replay=False, **kwargs):
        callback = EventCallback(function, self.bot, priority, **kwargs)
        if self._hook_notify:
            self._hook_notify(self, callback)
        self._hooks.append(callback)
        self._hooks.sort(key=lambda x: x.priority)

        if replay:
            for kwargs in self._stored_events:
                callback.call(self._make_event(kwargs))
        self._stored_events = None

    def _unhook(self, hook):
        self._hooks.remove(hook)

    def on(self, subevent, *extra_subevents, delimiter="."):
        if delimiter in subevent:
            event_chain = subevent.split(delimiter)
            event_obj = self
            for event_name in event_chain:
                event_obj = event_obj.get_child(event_name)
            return event_obj

        if extra_subevents:
            multiple_event_hook = MultipleEventHook()
            for extra_subevent in (subevent,)+extra_subevents:
                multiple_event_hook._add(self.get_child(extra_subevent))
            return multiple_event_hook

        return self.get_child(subevent)

    def call_for_result(self, default=None, max=None, **kwargs):
        results = self.call(max=max, **kwargs)
        return default if not len(results) else results[0]
    def assure_call(self, **kwargs):
        if not self._stored_events == None:
            self._stored_events.append(kwargs)
        else:
            self.call(**kwargs)
    def call(self, max=None, **kwargs):
        self.bot.log.debug("calling event: \"%s\" (params: %s)",
            [self._get_path(), kwargs])
        start = time.monotonic()

        event = self._make_event(kwargs)
        if self._call_notify:
            self._call_notify(self, event)

        called = 0
        returns = []
        for hook in self._hooks:
            if max and called == max:
                break
            if event.eaten:
                break
            try:
                returns.append(hook.call(event))
            except Exception as e:
                traceback.print_exc()
                # TODO don't make this an event call. can lead to error cycles!
                #self.bot.events.on("log").on("error").call(
                #    message="Failed to call event callback",
                #    data=traceback.format_exc())
            called += 1

        end = time.monotonic()
        total_milliseconds = (end - start) * 1000
        self.bot.log.debug("event called in %fms", [total_milliseconds])

        self.check_purge()

        return returns

    def get_child(self, child_name):
        child_name_lower = child_name.lower()
        if not child_name_lower in self._children:
            self._children[child_name_lower] = EventHook(self.bot,
                child_name, self)
            if self._child_notify:
                self._child_notify(self, self._children[
                    child_name_lower])
        return self._children[child_name_lower]

    def remove_child(self, child_name):
        child_name_lower = child_name.lower()
        if child_name_lower in self._children:
            del self._children[child_name_lower]
    def check_purge(self):
        if len(self._hooks) == 0 and len(self._children
                ) == 0 and not self.parent == None:
            self.parent.remove_child(self.name)
            self.parent.check_purge()

    def get_hooks(self):
        return self._hooks
    def get_children(self):
        return self._children.keys()
    def set_hook_notify(self, handler):
        self._hook_notify = handler
    def set_child_notify(self, handler):
        self._child_notify = handler
    def set_call_notify(self, handler):
        self._call_notify = handler
