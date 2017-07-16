import traceback

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
    def __init__(self, function, bot, **kwargs):
        self.function = function
        self.bot = bot
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
    def __init__(self, bot, name=None):
        self.bot = bot
        self.name = name
        self._children = {}
        self._hooks = []
        self._hook_notify = None
        self._child_notify = None
        self._call_notify = None
    def hook(self, function, **kwargs):
        callback = EventCallback(function, self.bot, **kwargs)
        if self._hook_notify:
            self._hook_notify(self, callback)
        self._hooks.append(callback)
    def _unhook(self, hook):
        self._hooks.remove(hook)
    def on(self, subevent, *extra_subevents):
        if extra_subevents:
            multiple_event_hook = MultipleEventHook()
            for extra_subevent in (subevent,)+extra_subevents:
                multiple_event_hook._add(self.get_child(extra_subevent))
            return multiple_event_hook
        return self.get_child(subevent)
    def call(self, max=None, **kwargs):
        if "data" in kwargs: kwargs.update(kwargs["data"].map())
        event = Event(self.bot, self.name, **kwargs)
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
        return returns
    def get_child(self, child_name):
        child_name_lower = child_name.lower()
        if not child_name_lower in self._children:
            self._children[child_name_lower] = EventHook(self.bot,
                child_name)
            if self._child_notify:
                self._child_notify(self, self._children[
                    child_name_lower])
        return self._children[child_name_lower]
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
