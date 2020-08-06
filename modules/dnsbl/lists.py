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
    def process(self, result):
        result = result.rsplit(".", 1)[1]
        if result == "1":
            return "proxy"
        elif result in ["2", "3"]:
            return "spamtap"
        elif result == "4":
            return "tor"
        elif result == "5":
            return "flooding"

class DroneBL(DNSBL):
    hostname = "dnsbl.dronebl.org"
    def process(self, result):
        result = result.rsplit(".", 1)[1]
        if result in ["8", "9", "10", "11", "14"]:
            return "proxy"
        elif result in ["3", "6", "7"]:
            return "flooding"
        elif result in ["12", "13", "15", "16"]:
            return "exploits"

class AbuseAtCBL(DNSBL):
    hostname = "cbl.abuseat.org"
    def process(self, result):
        result = result.rsplit(".", 1)[1]
        if result == "2":
            return "abuse"

DEFAULT_LISTS = [
    ZenSpamhaus(),
    EFNetRBL(),
    DroneBL(),
    AbuseAtCBL()
]

def default_lists():
    return collections.OrderedDict(
        (dnsbl.hostname, dnsbl) for dnsbl in DEFAULT_LISTS)
