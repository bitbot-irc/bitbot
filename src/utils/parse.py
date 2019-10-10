import io, typing
from src import utils

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
