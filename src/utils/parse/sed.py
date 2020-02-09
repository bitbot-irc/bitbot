import dataclasses, re, typing

class Sed(object):
    type: str
    def match(self, s: str) -> typing.Optional[str]:
        return None

@dataclasses.dataclass
class SedReplace(Sed):
    type: str
    pattern: typing.Pattern
    replace: str
    count: int

    def match(self, s):
        return self.pattern.sub(self.replace, s, self.count)

@dataclasses.dataclass
class SedMatch(Sed):
    type: str
    pattern: typing.Pattern

    def match(self, s):
        match = self.pattern.search(s)
        if match:
            return match.group(0)
        return None

def _sed_split(s):
    backslash = False
    forward_slash = []
    for i, c in enumerate(s):
        if not backslash:
            if c == "/":
                forward_slash.append(i)
            if c == "\\":
                backslash = True
        else:
            backslash = False
    if forward_slash and (not forward_slash[-1] == (len(s)-1)):
        forward_slash.append(len(s))

    last = 0
    out = []
    for i in forward_slash:
        out.append(s[last:i])
        last = i+1
    return out

def _sed_flags(s: str) -> typing.Tuple[int, int]:
    count = 1
    re_flags = 0
    if "g" in s:
        count = 0
    if "i" in s:
        re_flags |= re.I
    return count, re_flags

def parse_sed(sed_s: str) -> typing.Optional[Sed]:
    type, pattern, *args = _sed_split(sed_s)
    if type == "s":
        replace, *args = args
        count, flags = _sed_flags((args or [""])[0])
        pattern = re.compile(pattern, flags)
        return SedReplace(type, pattern, replace, count)
    elif type == "m":
        count, flags = _sed_flags((args or [""])[0])
        return SedMatch(type, re.compile(pattern, flags))
    return None

def sed(sed_obj: Sed, s: str) -> typing.Tuple[str, typing.Optional[str]]:
    out = sed_obj.match(s)
    return sed_obj.type, out
