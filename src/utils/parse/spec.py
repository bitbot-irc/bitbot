import enum, typing
from .time import duration
from .types import try_int
from src.utils.datetime.parse import date_human

class SpecArgumentContext(enum.IntFlag):
    CHANNEL = 1
    PRIVATE = 2
    ALL = 3

class SpecArgumentType(object):
    context = SpecArgumentContext.ALL

    def __init__(self, type_name: str, name: typing.Optional[str],
            exported: typing.Optional[str]):
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
class SpecArgumentTypeAdditionalWord(SpecArgumentType):
    def simple(self, args: typing.List[str]) -> typing.Tuple[typing.Any, int]:
        if len(args) > 1:
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
        if args:
            return " ".join(args), len(args)
        return None, 1
class SpecArgumentTypeTrimString(SpecArgumentTypeString):
    def simple(self, args: typing.List[str]):
        return SpecArgumentTypeString.simple(self, list(filter(None, args)))

class SpecArgumentTypeInt(SpecArgumentType):
    def simple(self, args):
        if args:
            return try_int(args[0]), 1
        return None, 1

class SpecArgumentTypeDuration(SpecArgumentType):
    def name(self):
        return "+%s" % (SpecArgumentType.name(self) or "duration")
    def simple(self, args: typing.List[str]) -> typing.Tuple[typing.Any, int]:
        if args:
            return duration(args[0]), 1
        return None, 1
    def error(self) -> typing.Optional[str]:
        return "Invalid timeframe"

class SpecArgumentTypeDate(SpecArgumentType):
    def name(self):
        return SpecArgumentType.name(self) or "yyyy-mm-dd"
    def simple(self, args):
        if args:
            return date_human(args[0], 1)
        return None, 1

class SpecArgumentPrivateType(SpecArgumentType):
    context = SpecArgumentContext.PRIVATE

SPEC_ARGUMENT_TYPES = {
    "word": SpecArgumentTypeWord,
    "aword": SpecArgumentTypeAdditionalWord,
    "wordlower": SpecArgumentTypeWordLower,
    "string": SpecArgumentTypeString,
    "tstring": SpecArgumentTypeTrimString,
    "int": SpecArgumentTypeInt,
    "date": SpecArgumentTypeDate,
    "duration": SpecArgumentTypeDuration
}

class SpecArgument(object):
    consume = True
    optional: bool = False
    types: typing.List[SpecArgumentType] = []

    @staticmethod
    def parse(optional: bool, argument_types: typing.List[str]):
        out: typing.List[SpecArgumentType] = []
        for argument_type in argument_types:
            exported = None
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

            out.append(argument_type_class(argument_type,
                argument_type_name, exported))

        spec_argument = SpecArgument()
        spec_argument.optional = optional
        spec_argument.types = out
        return spec_argument

    def format(self, context: SpecArgumentContext) -> typing.Optional[str]:
        if self.optional:
            format = "[%s]"
        else:
            format = "<%s>"

        names: typing.List[str] = []
        for argument_type in self.types:
            if not (context&argument_type.context) == 0:
                name = argument_type.name() or argument_type.type
                if name:
                    names.append(name)
        if names:
            return format % "|".join(names)
        return None

class SpecArgumentTypeLiteral(SpecArgumentType):
    def simple(self, args: typing.List[str]) -> typing.Tuple[typing.Any, int]:
        if args and args[0] == self.name():
            return args[0], 1
        return None, 1
    def error(self) -> typing.Optional[str]:
        return None
class SpecLiteralArgument(SpecArgument):
    @staticmethod
    def parse(optional: bool, literals: typing.List[str]) -> SpecArgument:
        spec_argument = SpecLiteralArgument()
        spec_argument.optional = optional
        spec_argument.types = [
            SpecArgumentTypeLiteral("literal", l, None) for l in literals]
        return spec_argument

    def format(self, context: SpecArgumentContext) -> typing.Optional[str]:
        return "|".join(t.name() or "" for t in self.types)

def argument_spec(spec: str) -> typing.List[SpecArgument]:
    out: typing.List[SpecArgument] = []
    for spec_argument in spec.split(" "):
        optional = spec_argument[0] == "?"

        if spec_argument[1] == "'":
            out.append(SpecLiteralArgument.parse(optional,
                spec_argument[2:].split(",")))
        else:
            consume = True
            if spec_argument[1] == "-":
                consume = False
                spec_argument = spec_argument[1:]

            spec_argument_obj = SpecArgument.parse(optional,
                spec_argument[1:].split("|"))
            spec_argument_obj.consume = consume
            out.append(spec_argument_obj)

    return out

def argument_spec_human(spec: typing.List[SpecArgument],
        context: SpecArgumentContext=SpecArgumentContext.ALL) -> str:
    arguments: typing.List[str] = []
    for spec_argument in spec:
        if spec_argument.consume:
            out = spec_argument.format(context)
            if out:
                arguments.append(out)
    return " ".join(arguments)
