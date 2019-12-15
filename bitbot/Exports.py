import typing

class Exports(object):
    def __init__(self):
        self._exports = {}
        self._context_exports = {}

    def new_context(self, context: str) -> "ExportsContext":
        return ExportsContext(self, context)

    def add(self, setting: str, value: typing.Any):
        self._add(None, setting, value)
    def _context_add(self, context: str, setting: str, value: typing.Any):
        self._add(context, setting, value)
    def _add(self, context: typing.Optional[str], setting: str,
            value: typing.Any):
        if context == None:
            if not setting in self._exports:
                self._exports[setting] = []
            self._exports[setting].append(value)
        else:
            if not context in self._context_exports:
                self._context_exports[context] = {}
            if not setting in self._context_exports[context]:
                self._context_exports[context][setting] = []
            self._context_exports[context][setting].append(value)

    def _get_keys(self):
        keys = list(self._exports.keys())
        for context in self._context_exports.keys():
            keys += list(self._context_exports[context].keys())
        return list(set(keys))

    def get_all(self, setting: str) -> typing.List[typing.Any]:
        return self._exports.get(setting, []) + sum([
            exports.get(setting, []) for exports in
            self._context_exports.values()], [])
    def get_one(self, setting: str, default: typing.Any=None
            ) -> typing.Optional[typing.Any]:
        values = self.get_all(setting)
        return values[0] if values else default

    def find(self, setting_prefix: str) -> typing.List[typing.Any]:
        found = []
        for key in self._get_keys():
            if key.startswith(setting_prefix):
                found.append(key)
        return found

    def purge_context(self, context: str):
        if context in self._context_exports:
            del self._context_exports[context]

class ExportsContext(object):
    def __init__(self, parent: Exports, context: str):
        self._parent = parent
        self.context = context

    def add(self, setting: str, value: typing.Any):
        self._parent._context_add(self.context, setting, value)
    def get_all(self, setting: str) -> typing.List[typing.Any]:
        return self._parent.get_all(setting)
    def get_one(self, setting: str, default: typing.Any=None
            ) -> typing.Optional[typing.Any]:
        return self._parent.get_one(setting, default)
    def find(self, setting_prefix: str) -> typing.List[typing.Any]:
        return self._parent.find(setting_prefix)
