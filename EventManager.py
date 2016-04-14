
class Event(object):
    def __init__(self, bot, **kwargs):
        self.bot = bot
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
    def __init__(self, bot):
        self.bot = bot
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
        event = Event(self.bot, **kwargs)
        if self._call_notify:
            self._call_notify(self, event)
        called = 0
        returns = []
        for hook in self._hooks:
            if max and called == max:
                break
            if event.eaten:
                break
            returns.append(hook.call(event))
            called += 1
        return returns
    def get_child(self, child_name):
        child_name_lower = child_name.lower()
        if not child_name_lower in self._children:
            self._children[child_name_lower] = EventHook(self.bot)
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
