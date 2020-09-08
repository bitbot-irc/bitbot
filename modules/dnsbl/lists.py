import collections

class DNSBL(object):
    def __init__(self, hostname=None):
        if not hostname == None:
            self.hostname = hostname

    def process(self, result: str):
        return result

class ZenSpamhaus(DNSBL):
    hostname = "zen.spamhaus.org"
    def process(self, result):
        result = result.rsplit(".", 1)[1]
        if result in ["2", "3", "9"]:
            desc = "spam"
        elif result in ["4", "5", "6", "7"]:
            desc = "exploits"
        return f"{result} - {desc}"

class EFNetRBL(DNSBL):
    hostname = "rbl.efnetrbl.org"
    def process(self, result):
        result = result.rsplit(".", 1)[1]
        if result == "1":
            desc = "proxy"
        elif result in ["2", "3"]:
            desc = "spamtap"
        elif result == "4":
            desc = "tor"
        elif result == "5":
            desc = "flooding"
        return f"{result} - {desc}"

DRONEBL_CATEGORIES = {
    3:  "IRC drone",
    5:  "bottler",
    6:  "unknown spambot or drone",
    7:  "DDoS drone",
    8:  "open SOCKS proxy",
    9:  "open HTTP proxy",
    10: "proxychain",
    11: "web page proxy",
    12: "open DNS resolver",
    13: "brute force attacker",
    14: "open WINGATE proxy",
    15: "compromised router/gateway",
    16: "autorooting malware",
    17: "detected botnet IP",
    18: "DNS/MX on IRC",
    19: "abused VPN service"
}
class DroneBL(DNSBL):
    hostname = "dnsbl.dronebl.org"
    def process(self, result):
        result = int(result.rsplit(".", 1)[1])
        desc   = DRONEBL_CATEGORIES.get(result, "unknown")
        return f"{result} - {desc}"

class AbuseAtCBL(DNSBL):
    hostname = "cbl.abuseat.org"
    def process(self, result):
        result = result.rsplit(".", 1)[1]
        if result == "2":
            desc = "abuse"
        else:
            desc = "unknown"
        return f"{result} - {desc}"

DEFAULT_LISTS = [
    ZenSpamhaus(),
    EFNetRBL(),
    DroneBL(),
    AbuseAtCBL()
]

def default_lists():
    return collections.OrderedDict(
        (dnsbl.hostname, dnsbl) for dnsbl in DEFAULT_LISTS)
