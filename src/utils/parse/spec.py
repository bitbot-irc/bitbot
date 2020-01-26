import enum, typing
from .time import duration

class SpecArgumentContext(enum.IntFlag):
    CHANNEL = 1
    PRIVATE = 2
    ALL = 3

class SpecArgumentType(object):
    context = SpecArgumentContext.ALL

    def __init__(self, type_name: str, name: typing.Optional[str], exported: str):
        self.type = type_name
        self._name = name
        self.exported = exported

    def name(self) -> typing.Optional[str]:
        return self._name
    def simple(self, args: typing.List[str]) -> typing.Tuple[typing.Any, int]:
        return None, -1
    def error(self) -> typing.Optional[str]:
        return None

class SpecArgumentTypeWord(SpecArgumentType):
    def simple(self, args: typing.List[str]) -> typing.Tuple[typing.Any, int]:
        if args:
            return args[0], 1
        return None, 1
class SpecArgumentTypeWordLower(SpecArgumentTypeWord):
    def simple(self, args: typing.List[str]) -> typing.Tuple[typing.Any, int]:
        out = SpecArgumentTypeWord.simple(self, args)
        if out[0]:
            return out[0].lower(), out[1]
        return out

class SpecArgumentTypeString(SpecArgumentType):
    def name(self):
        return "%s ..." % SpecArgumentType.name(self)
    def simple(self, args: typing.List[str]) -> typing.Tuple[typing.Any, int]:
        return " ".join(args), len(args)

class SpecArgumentTypeDuration(SpecArgumentType):
    def name(self):
        return "+%s" % (SpecArgumentType.name(self) or "duration")
    def simple(self, args: typing.List[str]) -> typing.Tuple[typing.Any, int]:
        if args:
            return duration(args[0]), 1
        return None, 1
    def error(self) -> typing.Optional[str]:
        return "Invalid timeframe"

class SpecArgumentPrivateType(SpecArgumentType):
    context = SpecArgumentContext.PRIVATE

SPEC_ARGUMENT_TYPES = {
    "word": SpecArgumentTypeWord,
    "wordlower": SpecArgumentTypeWordLower,
    "string": SpecArgumentTypeString,
    "duration": SpecArgumentTypeDuration
}

class SpecArgument(object):
    def __init__(self, optional: bool, types: typing.List[SpecArgumentType]):
        self.optional = optional
        self.types = types

def argument_spec(spec: str) -> typing.List[SpecArgument]:
    out: typing.List[SpecArgument] = []
    for spec_argument in spec.split(" "):
        optional = spec_argument[0] == "?"

        argument_types: typing.List[SpecArgumentType] = []
        for argument_type in spec_argument[1:].split("|"):
            exported = ""
            if "~" in argument_type:
                exported = argument_type.split("~", 1)[1]
                argument_type = argument_type.replace("~", "", 1)

            argument_type_name: typing.Optional[str] = None
            name_end = argument_type.find(">")
            if argument_type.startswith("<") and name_end > 0:
                argument_type_name = argument_type[1:name_end]
                argument_type = argument_type[name_end+1:]

            argument_type_class = SpecArgumentType
            if argument_type in SPEC_ARGUMENT_TYPES:
                argument_type_class = SPEC_ARGUMENT_TYPES[argument_type]
            elif exported:
                argument_type_class = SpecArgumentPrivateType

            argument_types.append(argument_type_class(argument_type,
                argument_type_name, exported))
        out.append(SpecArgument(optional, argument_types))
    return out

def argument_spec_human(spec: typing.List[SpecArgument],
        context: SpecArgumentContext=SpecArgumentContext.ALL) -> str:
    out: typing.List[str] = []
    for spec_argument in spec:
        names: typing.List[str] = []
        for argument_type in spec_argument.types:
            if not (context&argument_type.context) == 0:
                name = argument_type.name() or argument_type.type
                if name:
                    names.append(name)

        if names:
            if spec_argument.optional:
                format = "[%s]"
            else:
                format = "<%s>"
            out.append(format % "|".join(names))
    return " ".join(out)
