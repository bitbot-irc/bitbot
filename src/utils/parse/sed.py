import dataclasses, re, typing

def _tokens(s: str, token: str) -> typing.List[int]:
    backslash = False
    tokens = []
    for i, c in enumerate(s):
        if not backslash:
            if c == token:
                tokens.append(i)
            elif c == "\\":
                backslash = True
        else:
            backslash = False
    return tokens

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
        replace_copy = self.replace
        for token in reversed(_tokens(replace_copy, "&")):
            replace_copy = replace_copy[:token]+r"\g<0>"+replace_copy[token+1:]
        s = re.sub(self.pattern, replace_copy, s, self.count)
        return s

@dataclasses.dataclass
class SedMatch(Sed):
    type: str
    pattern: typing.Pattern

    def match(self, s):
        match = self.pattern.search(s)
        if match:
            return match.group(0)
        return None

def _sed_split(s: str) -> typing.List[str]:
    tokens = _tokens(s, "/")
    if tokens and (not tokens[-1] == (len(s)-1)):
        tokens.append(len(s))

    last = 0
    out = []
    for i in tokens:
        out.append(s[last:i].replace("\\/", "/"))
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

def parse(sed_s: str) -> typing.Optional[Sed]:
    type, pattern, *args = _sed_split(sed_s)
    if type == "s":
        replace, *args = args
        count, flags = _sed_flags((args or [""])[0])
        pattern_re = re.compile(pattern, flags)
        return SedReplace(type, pattern_re, replace, count)
    elif type == "m":
        count, flags = _sed_flags((args or [""])[0])
        return SedMatch(type, re.compile(pattern, flags))
    return None

def sed(sed_obj: Sed, s: str) -> typing.Tuple[str, typing.Optional[str]]:
    out = sed_obj.match(s)
    return sed_obj.type, out
