import typing

BITBOT_MAGIC = "__bitbot"

class BitBotMagic(object):
    def __init__(self):
        self._hooks: typing.List[typing.Tuple[str, dict]] = []
        self._kwargs: typing.List[typing.Tuple[str, typing.Any]] = []
        self._exports: typing.List[typing.Tuple[str, typing.Any]] = []
    def add_hook(self, hook: str, kwargs: dict):
        self._hooks.append((hook, kwargs))
    def add_kwarg(self, key: str, value: typing.Any):
        self._kwargs.append((key, value))

    def get_hooks(self):
        hooks: typing.List[typing.Tuple[str, typing.List[Tuple[str, typing.Any]]]] = []
        for hook, kwargs in self._hooks:
            hooks.append((hook, self._kwargs.copy()+list(kwargs.items())))
        return hooks

    def add_export(self, key: str, value: typing.Any):
        self._exports.append((key, value))
    def get_exports(self):
        return self._exports.copy()

def get_magic(obj: typing.Any):
    if not has_magic(obj):
        setattr(obj, BITBOT_MAGIC, BitBotMagic())
    return getattr(obj, BITBOT_MAGIC)
def has_magic(obj: typing.Any):
    return hasattr(obj, BITBOT_MAGIC)

def hook(event: str, **kwargs):
    def _hook_func(func):
        magic = get_magic(func)
        magic.add_hook(event, kwargs)
        return func
    return _hook_func
def export(setting: str, value: typing.Any):
    def _export_func(module):
        magic = get_magic(module)
        magic.add_export(setting, value)
        return module
    return _export_func
def kwarg(key: str, value: typing.Any):
    def _kwarg_func(func):
        magic = get_magic(func)
        magic.add_kwarg(key, value)
        return func
    return _kwarg_func

