import decimal, io, random, typing
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

def timed_args(args, min_args):
    if args and args[0][0] == "+":
        if len(args[1:]) < min_args:
            raise errors.EventError("Not enough arguments")
        time = datetime.from_pretty_time(args[0][1:])
        if time == None:
            raise errors.EventError("Invalid timeframe")
        return time, args[1:]
    return None, args

SHORTENCODE_CHARS = list(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789")

SHORTENCODE_SALT = "bitbot"
def _shortencode_salt(salt: str):
    chars = SHORTENCODE_CHARS.copy()
    random.Random(salt).shuffle(chars)
    return chars

def _shortencode_tobase(n: int, base: int) -> typing.List[int]:
    r = []
    while n:
        n, remainder = divmod(n, base)
        r.append(remainder)
    return r
def _shortencode_frombase(ints: typing.List[int], base: int) -> int:
    n = 0
    for i in ints:
        n = (n*base)+i
    return n

def shortencode_b(bytes: bytes, salt: str=SHORTENCODE_SALT):
    chars = _shortencode_salt(salt)

    ints = list(bytes)
    n = _shortencode_frombase(ints, 256)
    r = _shortencode_tobase(n, len(chars))

    return "".join(chars[i] for i in reversed(r))
def shortencode(s: str, salt: str=SHORTENCODE_SALT):
    return shortencode_b(s.encode("latin-1"), salt)

def shortdecode_b(s: str, salt: str=SHORTENCODE_SALT):
    chars = _shortencode_salt(salt)

    ints = [chars.index(c) for c in s]
    n = _shortencode_frombase(ints, len(chars))
    r = _shortencode_tobase(n, 256)

    return bytes(reversed(r))
def shortdecode(s: str, salt: str=SHORTENCODE_SALT):
    return shortdecode_b(s, salt).decode("latin-1")
