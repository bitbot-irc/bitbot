import decimal, enum, io, typing
from . import datetime, errors

COMMENT_TYPES = ["#", "//"]
def hashflags(filename: str
        ) -> typing.List[typing.Tuple[str, typing.Optional[str]]]:
    hashflags = [] # type: typing.List[typing.Tuple[str, typing.Optional[str]]]
    with io.open(filename, mode="r", encoding="utf8") as f:
        for line in f:
            line = line.strip("\n")
            found = False
            for comment_type in COMMENT_TYPES:
                if line.startswith(comment_type):
                    line = line.replace(comment_type, "", 1).lstrip()
                    found = True
                    break

            if not found:
                break
            elif line.startswith("--"):
                hashflag, sep, value = line[2:].partition(" ")
                hashflags.append((hashflag, (value if sep else None)))
    return hashflags

class Docstring(object):
    def __init__(self, description: str, items: typing.Dict[str, str],
            var_items: typing.Dict[str, typing.List[str]]):
        self.description = description
        self.items = items
        self.var_items = var_items

def docstring(s: str) -> Docstring:
    description = ""
    last_item = None
    last_item_no_space = False
    items = {} # type: typing.Dict[str, str]
    var_items = {} # type: typing.Dict[str, typing.List[str]]
    if s:
        for line in s.split("\n"):
            line = line.strip()

            if line:
                if line[0] == ":":
                    key, _, value = line[1:].partition(": ")
                    last_item = key.lstrip("-")
                    last_item_no_space = key.startswith("-")

                    if key in var_items:
                        var_items[last_item].append(value)
                    elif key in items:
                        var_items[last_item] = [items.pop(last_item), value]
                    else:
                        items[last_item] = value
                else:
                    if last_item:
                        if last_item_no_space:
                            items[last_item] += line
                        else:
                            items[last_item] += " %s" % line
                    else:
                        if description:
                            description += " "
                        description += line
    return Docstring(description, items, var_items)

def keyvalue(s: str, delimiter: str=" "
        ) -> typing.Dict[str, typing.Optional[str]]:
    items = {} # type: typing.Dict[str, typing.Optional[str]]
    pairs = s.split(delimiter)
    for pair in filter(None, pairs):
        key, sep, value = pair.partition("=")
        if sep:
            items[key] = value
        else:
            items[key] = None
    return items

def try_int(s: str) -> typing.Optional[int]:
    try:
        return int(s)
    except ValueError:
        return None

def line_normalise(s: str) -> str:
    lines = list(filter(None, [line.strip() for line in s.split("\n")]))
    return "  ".join(line.replace("  ", " ") for line in lines)

def parse_number(s: str) -> str:
    try:
        decimal.Decimal(s)
        return s
    except:
        pass

    unit = s[-1].lower()
    number_str = s[:-1]
    try:
        number = decimal.Decimal(number_str)
    except:
        raise ValueError("Invalid format '%s' passed to parse_number" %
            number_str)

    if unit == "k":
        number *= decimal.Decimal("1_000")
    elif unit == "m":
        number *= decimal.Decimal("1_000_000")
    elif unit == "b":
        number *= decimal.Decimal("1_000_000_000")
    else:
        raise ValueError("Unknown unit '%s' given to parse_number" % unit)
    return str(number)

def duration(s: str):
    if s[0] == "+":
        duration = datetime.from_pretty_time(s[1:])
        if not duration == None:
            return duration
    return None

def format_tokens(s: str, names: typing.List[str], sigil: str="$"
        ) -> typing.List[typing.Tuple[int, str]]:
    names = names.copy()
    names.sort()
    names.reverse()

    i = 0
    max = len(s)-1
    sigil_found = False
    tokens: typing.List[typing.Tuple[int, str]] = []

    while i < max:
        if s[i] == sigil:
            i += 1
            if not s[i] == sigil:
                for name in names:
                    if len(name) <= (len(s)-i) and s[i:i+len(name)] == name:
                        tokens.append((i-1, "%s%s" % (sigil, name)))
                        i += len(name)
                        break
            else:
                tokens.append((i-1, "$$"))
        i += 1
    return tokens

def format_token_replace(s: str, vars: typing.Dict[str, str],
        sigil: str="$") -> str:
    vars = vars.copy()
    vars.update({sigil: sigil})
    tokens = format_tokens(s, list(vars.keys()), sigil)
    tokens.sort(key=lambda x: x[0])
    tokens.reverse()
    for i, token in tokens:
        s = s[:i] + vars[token.replace(sigil, "", 1)] + s[i+len(token):]
    return s

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
