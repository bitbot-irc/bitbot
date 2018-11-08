import io, typing

COMMENT_TYPES = ["#", "//"]
def hashflags(filename: str) -> typing.List[typing.Tuple[str, str]]:
    hashflags = {}
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
                hashflags[hashflag] = value if sep else None
    return list(hashflags.items())

class Docstring(object):
    def __init__(self, description: str, items: typing.Dict[str, str],
            var_items: typing.Dict[str, typing.List[str]]):
        self.description = description
        self.items = items
        self.var_items = var_items

def docstring(s: str) -> Docstring:
    description = ""
    last_item = None
    items = {} # type: typing.Dict[str, str]
    var_items = {} # type: typing.Dict[str, typing.List[str]]
    if s:
        for line in s.split("\n"):
            line = line.strip()

            if line:
                if line[0] == ":":
                    key, _, value = line[1:].partition(": ")
                    last_item = key

                    if key in var_items:
                        var_items[key].append(value)
                    elif key in items:
                        var_items[key] = [items.pop(key), value]
                    else:
                        items[key] = value
                else:
                    if last_item:
                        items[last_item] += " %s" % line
                    else:
                        if description:
                            description += " "
                        description += line
    return Docstring(description, items, var_items)

def keyvalue(s, delimiter: str=" ") -> typing.Dict[str, str]:
    items = {}
    pairs = s.split(delimiter)
    for pair in filter(None, pairs):
        key, sep, value = pair.partition("=")
        if sep:
            items[key] = value
        else:
            items[key] = None
    return items
