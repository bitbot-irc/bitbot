

class ExportsContext(object):
    def __init__(self, parent, context):
        self._parent = parent
        self.context = context

    def add(self, setting, value):
        self._parent._context_add(self.context, setting, value)
    def get_all(self, setting):
        return self._parent.get_all(setting)

class Exports(object):
    def __init__(self):
        self._exports = {}
        self._context_exports = {}

    def new_context(self, context):
        return ExportsContext(self, context)

    def add(self, setting, value):
        self._add(None, setting, value)
    def _context_add(self, context, setting, value):
        self._add(context, setting, value)
    def _add(self, context, setting, value):
        if context == None:
            if not setting in self_exports:
                self._exports[setting] = []
            self._exports[setting].append(value)
        else:
            if not context in self._context_exports:
                self._context_exports[context] = {}
            if not setting in self._context_exports[context]:
                self._context_exports[context][setting] = []
            self._context_exports[context][setting].append(value)

    def get_all(self, setting):
        return self._exports.get(setting, []) + sum([
            exports.get(setting, []) for exports in
            self._context_exports.values()], [])

    def purge_context(self, context):
        if context in self._context_exports:
            del self._context_exports[context]
