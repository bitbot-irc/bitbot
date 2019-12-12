import collections

class DNSBL(object):
    def __init__(self, hostname=None):
        if not hostname == None:
            self.hostname = hostname

    def process(self, result: str):
        return "unknown"

class ZenSpamhaus(DNSBL):
    hostname = "zen.spamhaus.org"
    def process(self, result):
        result = result.rsplit(".", 1)[1]
        if result in ["2", "3", "9"]:
            return "spam"
        elif result in ["4", "5", "6", "7"]:
            return "exploits"
class EFNetRBL(DNSBL):
    hostname = "rbl.efnetrbl.org"
    SPAMTRAP = ["2", "3"]
    def process(self, result):
        result = result.rsplit(".", 1)[1]
        if result == "1":
            return "proxy"
        elif result in self.SPAMTRAP:
            return "spamtap"
        elif result == "4":
            return "tor"
        elif result == "5":
            return "flooding"

DEFAULT_LISTS = [
    ZenSpamhaus(),
    EFNetRBL()
]

def default_lists():
    return collections.OrderedDict(
        (dnsbl.hostname, dnsbl) for dnsbl in DEFAULT_LISTS)
