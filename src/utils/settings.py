import typing

class SettingParseException(Exception):
    pass

class Setting(object):
    example: typing.Optional[str] = None
    def __init__(self, name: str, help: str=None, example: str=None):
        self.name = name
        self.help = help
        if not example == None:
            self.example = example
    def parse(self, value: str) -> typing.Any:
        return value

    def get_example(self):
        if not self.example == None:
            return "Example: %s" % self.example
        else:
            return self._format_example()
    def _format_example(self):
        return None

    def format(self, value: typing.Any):
        return repr(value)

SETTING_TRUE = ["true", "yes", "on", "y", "1"]
SETTING_FALSE = ["false", "no", "off", "n", "0"]
class BoolSetting(Setting):
    example: typing.Optional[str] = "on"
    def parse(self, value: str) -> typing.Any:
        value_lower = value.lower()
        if value_lower in SETTING_TRUE:
            return True
        elif value_lower in SETTING_FALSE:
            return False
        return None

class IntSetting(Setting):
    example: typing.Optional[str] = "10"
    def parse(self, value: str) -> typing.Any:
        if value == "0":
            return 0
        else:
            stripped = value.lstrip("0")
            if stripped.isdigit():
                return int(stripped)
        return None

class IntRangeSetting(IntSetting):
    example: typing.Optional[str] = None
    def __init__(self, n_min: int, n_max: typing.Optional[int], name: str,
            help: str=None, example: str=None):
        self._n_min = n_min
        self._n_max = n_max
        Setting.__init__(self, name, help, example)

    def parse(self, value: str) -> typing.Any:
        out = IntSetting.parse(self, value)
        if (not out == None and
                self._n_min <= out and
                (self._n_max == None or out <= self._n_max)):
            return out
        return None

    def _format_example(self):
        return "Must be between %d and %d" % (self._n_min, self._n_max)

class OptionsSetting(Setting):
    def __init__(self, options: typing.List[str], name: str, help: str=None,
            example: str=None,
            options_factory: typing.Callable[[], typing.List[str]]=None):
        self._options = options
        self._options_factory = options_factory
        Setting.__init__(self, name, help, example)

    def _get_options(self):
        if not self._options_factory == None:
            return self._options_factory()
        else:
            return self._options

    def parse(self, value: str) -> typing.Any:
        value_lower = value.lower()
        for option in self._get_options():
            if option.lower() == value_lower:
                return option
        return None

    def _format_example(self):
        options = self._get_options()
        options_str = ["'%s'" % option for option in options]
        return "Options: %s" % ", ".join(options_str)

class FunctionSetting(Setting):
    def __init__(self, func: typing.Callable[[str], bool], name: str,
            help: str=None, example: str=None, format=None):
        self._func = func
        Setting.__init__(self, name, help, example)
        if not format == None:
            self.format = format # type: ignore

    def parse(self, value: str) -> typing.Any:
        return self._func(value)

def sensitive_format(value: typing.Any):
    return "*"*16

class SensitiveSetting(Setting):
    def format(self, value: typing.Any):
        return sensitive_format(value)

